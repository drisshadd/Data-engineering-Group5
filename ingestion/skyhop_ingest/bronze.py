"""Write to Snowflake BRONZE. Only three kinds of statement, all replay-safe:

  PUT  ... OVERWRITE=FALSE      the same file sent twice is skipped (status SKIPPED)
  COPY INTO ... (no FORCE)      Snowflake remembers loaded files for 64 days: a replay loads 0 rows
  MERGE INTO API_RAW            keyed on (source, request_key): a re-pull updates, never duplicates
"""
from __future__ import annotations

import csv
import json
import logging
import os
from pathlib import Path

log = logging.getLogger("skyhop.bronze")
STAGE = "@SKYHOP.BRONZE.LANDING"
AREA = {"flights": "flight_ops", "airports": "flight_ops", "bookings": "reservations", "passengers": "reservations"}
TABLES = ("airports", "flights", "passengers", "bookings")


def connect():
    import snowflake.connector  # imported lazily: unit tests run without Snowflake

    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],            # <org>-<account>
        user=os.environ["SNOWFLAKE_USER"],
        private_key_file=os.environ["SNOWFLAKE_PRIVATE_KEY_FILE"],
        role=os.environ.get("SNOWFLAKE_ROLE", "SKYHOP_INGEST"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "SKYHOP_WH"),
        database="SKYHOP", schema="BRONZE",
        session_parameters={"QUERY_TAG": "skyhop-ingest"},
    )


def stage_dir(table: str, batch: int) -> str:
    return f"{AREA[table]}/batch_{batch:03d}"


def put_file(cur, local: Path, table: str, batch: int) -> str:
    cur.execute(f"PUT 'file://{Path(local).resolve().as_posix()}' {STAGE}/{stage_dir(table, batch)}/ "
                f"AUTO_COMPRESS=TRUE OVERWRITE=FALSE")
    rows = cur.fetchall()
    status = rows[0][6] if rows and len(rows[0]) > 6 else "?"
    log.info("PUT %-16s -> %s/%s : %s", Path(local).name, STAGE, stage_dir(table, batch), status)
    return status


def copy_sql(table: str) -> str:
    return (f"COPY INTO SKYHOP.BRONZE.{table.upper()} FROM {STAGE}/{AREA[table]}/ "
            f"PATTERN = '.*batch_[0-9]+/{table}[.]csv([.]gz)?' "
            f"FILE_FORMAT = (FORMAT_NAME = SKYHOP.BRONZE.CSV_RAW) MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE "
            f"INCLUDE_METADATA = (_SOURCE_FILE = METADATA$FILENAME, _LOADED_AT = METADATA$START_SCAN_TIME) "
            f"ON_ERROR = ABORT_STATEMENT")


def copy_table(cur, table: str) -> int:
    cur.execute(copy_sql(table))
    loaded = 0
    for r in cur.fetchall():
        # loaded file: (file, status, rows_parsed, rows_loaded, ...) ; nothing new: ('Copy executed with 0 files processed.',)
        if len(r) >= 4 and isinstance(r[3], int):
            loaded += r[3]
            log.info("COPY %-10s %s %s rows=%s", table, r[0], r[1], r[3])
    if loaded == 0:
        log.info("COPY %-10s 0 new file (already loaded: replay-safe)", table)
    return loaded


def load_files(cur, data_dir: Path, batch: int, tables=("flights", "airports"), as_batch: int | None = None) -> dict:
    """Source 1 (flight-ops file drop). Also the fallback for reservations when PostgreSQL is not available."""
    folder = Path(data_dir) / f"batch_{batch:03d}"
    target = as_batch if as_batch is not None else batch
    out = {}
    for t in tables:
        f = folder / f"{t}.csv"
        if not f.exists():
            log.info("no %s in %s (normal: dimensions are not re-sent every day)", f.name, folder)
            continue
        put_file(cur, f, t, target)
    for t in tables:
        out[t] = copy_table(cur, t)
    return out


def merge_api(cur, source, entity, key, payload):
    cur.execute(
        """MERGE INTO SKYHOP.BRONZE.API_RAW t
           USING (SELECT %s AS source, %s AS entity, %s AS request_key, PARSE_JSON(%s) AS payload) s
           ON t.source = s.source AND t.request_key = s.request_key
           WHEN MATCHED THEN UPDATE SET payload = s.payload, entity = s.entity, _loaded_at = CURRENT_TIMESTAMP()
           WHEN NOT MATCHED THEN INSERT (source, entity, request_key, payload, _loaded_at)
                VALUES (s.source, s.entity, s.request_key, s.payload, CURRENT_TIMESTAMP())""",
        (source, entity, key, json.dumps(payload)))


# ------------------------------------------------------------------------------- verification
def expected_counts(data_dir: Path) -> dict:
    """Rows per file in the generator output = rows bronze must hold per _source_file."""
    out = {}
    for folder in sorted(Path(data_dir).glob("batch_*")):
        b = int(folder.name.split("_")[1])
        for f in sorted(folder.glob("*.csv")):
            with open(f, newline="", encoding="utf-8") as fh:
                n = sum(1 for _ in csv.DictReader(fh))
            out[f"{stage_dir(f.stem, b)}/{f.stem}.csv.gz"] = n
    return out


def verify(cur, expected: dict) -> list[tuple]:
    actual = {}
    for t in TABLES:
        cur.execute(f"SELECT _source_file, COUNT(*) FROM SKYHOP.BRONZE.{t.upper()} GROUP BY 1")
        actual.update({k: v for k, v in cur.fetchall()})
    report = []
    for k in sorted(set(expected) | set(actual)):
        e, a = expected.get(k), actual.get(k)
        report.append((k, e, a, "OK" if e == a else ("NOT EXPECTED" if e is None else "MISMATCH")))
    return report
