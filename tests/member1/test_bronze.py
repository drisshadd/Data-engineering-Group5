"""Bronze loading without Snowflake: a fake cursor records the SQL. Checks the replay-safe options,
the stage folder convention, the watermark rule and the 'bronze finished' verification."""
import json
from pathlib import Path

from skyhop_ingest import bronze, postgres_extract

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "generator" / "out" / "skyhop"
EXPECTED = json.loads((ROOT / "docs" / "member1" / "bronze_expected_counts.json").read_text())


class FakeCursor:
    def __init__(self, counts=None, watermark=0):
        self.sql, self.counts, self.watermark, self._last = [], counts or {}, watermark, None

    def execute(self, q, params=None):
        self.sql.append((q, params))
        self._last = q
        return self

    def fetchall(self):
        q = self._last
        if q.startswith("PUT"):
            return [("f.csv", "f.csv.gz", 1, 1, "NONE", "GZIP", "UPLOADED", "")]
        if q.startswith("COPY"):
            return [("flight_ops/batch_001/flights.csv.gz", "LOADED", 928, 928, 1, 0, None, None, None, None)]
        if "GROUP BY 1" in q:
            t = q.split("BRONZE.")[1].split()[0].lower()
            return [(k, v) for k, v in self.counts.items() if f"/{t}.csv" in k]
        return []

    def fetchone(self):
        return (self.watermark,)


def test_expected_counts_match_generator():
    assert bronze.expected_counts(DATA) == EXPECTED
    assert sum(EXPECTED.values()) == 13749


def test_files_put_without_overwrite_and_copy_without_force():
    cur = FakeCursor()
    bronze.load_files(cur, DATA, 1, ("flights", "airports"))
    puts = [q for q, _ in cur.sql if q.startswith("PUT")]
    copies = [q for q, _ in cur.sql if q.startswith("COPY")]
    assert len(puts) == 2 and all("OVERWRITE=FALSE" in q for q in puts)
    assert any("/flight_ops/batch_001/" in q and "flights.csv" in q for q in puts)
    assert len(copies) == 2 and not any("FORCE" in q for q in copies)
    assert all("MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE" in q and "_SOURCE_FILE = METADATA$FILENAME" in q for q in copies)


def test_batch2_without_airports_file_is_fine_and_reservations_go_to_their_area():
    cur = FakeCursor()
    bronze.load_files(cur, DATA, 2, ("passengers", "bookings"))
    puts = [q for q, _ in cur.sql if q.startswith("PUT")]
    assert all("/reservations/batch_002/" in q for q in puts) and len(puts) == 2


def test_as_batch_for_incident_rehearsal():
    cur = FakeCursor()
    bronze.load_files(cur, DATA, 1, ("bookings",), as_batch=3)
    assert "/reservations/batch_003/" in cur.sql[0][0]


def test_verify_ok_and_detects_extra_or_missing_file():
    assert all(s == "OK" for *_, s in bronze.verify(FakeCursor(counts=EXPECTED), EXPECTED))
    extra = dict(EXPECTED, **{"reservations/batch_003/bookings.csv.gz": 2300})
    rep = {k: s for k, _, _, s in bronze.verify(FakeCursor(counts=extra), EXPECTED)}
    assert rep["reservations/batch_003/bookings.csv.gz"] == "NOT EXPECTED"
    doubled = {k: v * 2 for k, v in EXPECTED.items()}
    assert all(s == "MISMATCH" for *_, s in bronze.verify(FakeCursor(counts=doubled), EXPECTED))


class FakePg:
    """PostgreSQL with batches 1 and 2 (as load_to_postgres.py leaves it)."""
    def __init__(self):
        self.q, self.description = None, None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def cursor(self):
        return self

    def execute(self, q, params=None):
        self.q, self.params = q, params
        if q.startswith("SELECT *"):
            self.description = [("booking_id",), ("fare_gbp",), ("_batch",), ("_loaded_at",)]

    def fetchall(self):
        if "DISTINCT _batch" in self.q:
            return [(b,) for b in (1, 2) if b > self.params[0]]
        return [("1", "£10.00", self.params[0], None), ("2", None, self.params[0], None)]


def test_postgres_incremental_moves_watermark_after_copy_only():
    cur = FakeCursor(watermark=1)
    done = postgres_extract.extract(cur, lambda: FakePg())
    assert done == [2]                                        # batch 1 already loaded -> only batch 2
    order = [q.split()[0] for q, _ in cur.sql if q.split()[0] in ("PUT", "COPY", "INSERT")]
    assert order.index("INSERT") > max(i for i, k in enumerate(order) if k == "COPY")
    wm = [p for q, p in cur.sql if q.startswith("INSERT INTO SKYHOP.BRONZE.INGEST_WATERMARK")]
    assert wm == [("postgres_reservations", 2)]


def test_postgres_nothing_new_is_a_noop():
    cur = FakeCursor(watermark=2)
    assert postgres_extract.extract(cur, lambda: FakePg()) == []
    assert not any(q.startswith(("PUT", "COPY", "INSERT")) for q, _ in cur.sql)
