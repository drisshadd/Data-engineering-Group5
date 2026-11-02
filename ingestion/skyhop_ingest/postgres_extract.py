"""Source 2: SkyHop reservation system = PostgreSQL (loaded by generator/load_to_postgres.py).

Incremental extract by watermark on the _batch column. The watermark lives in Snowflake
(BRONZE.INGEST_WATERMARK) and moves ONLY after PUT + COPY succeeded: a crash in the middle re-sends the
same batch next time, which is harmless (PUT/COPY skip known files).
"""
from __future__ import annotations

import csv
import logging
import os
import tempfile
from pathlib import Path

from . import bronze

log = logging.getLogger("skyhop.postgres")
SOURCE = "postgres_reservations"
TABLES = ("passengers", "bookings")


def read_watermark(cur) -> int:
    cur.execute("SELECT COALESCE(MAX(last_batch), 0) FROM SKYHOP.BRONZE.INGEST_WATERMARK WHERE source = %s", (SOURCE,))
    return int(cur.fetchone()[0])


def new_batches(pc, company: str, watermark: int) -> list[int]:
    pc.execute(f"SELECT DISTINCT _batch FROM {company}.bookings WHERE _batch > %s "
               f"UNION SELECT DISTINCT _batch FROM {company}.passengers WHERE _batch > %s ORDER BY 1",
               (watermark, watermark))
    return [r[0] for r in pc.fetchall()]


def export_batch(pc, company: str, table: str, batch: int, out: Path) -> int:
    pc.execute(f"SELECT * FROM {company}.{table} WHERE _batch = %s", (batch,))
    cols = [d[0] for d in pc.description]
    keep = [i for i, c in enumerate(cols) if c not in ("_batch", "_loaded_at")]
    rows = pc.fetchall()
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([cols[i] for i in keep])
        for r in rows:
            w.writerow(["" if r[i] is None else r[i] for i in keep])
    return len(rows)


def extract(cur, pg_connect, company: str = "skyhop") -> list[int]:
    wm = read_watermark(cur)
    with pg_connect() as pg, pg.cursor() as pc:
        batches = new_batches(pc, company, wm)
        log.info("postgres watermark=%s new batches=%s", wm, batches or "none")
        for b in batches:
            with tempfile.TemporaryDirectory() as tmp:
                for t in TABLES:
                    f = Path(tmp) / f"{t}.csv"
                    n = export_batch(pc, company, t, b, f)
                    if n:
                        bronze.put_file(cur, f, t, b)
                    log.info("extracted %s batch %s: %d rows", t, b, n)
            for t in TABLES:
                bronze.copy_table(cur, t)
            cur.execute("INSERT INTO SKYHOP.BRONZE.INGEST_WATERMARK (source, last_batch, updated_at) "
                        "VALUES (%s, %s, CURRENT_TIMESTAMP())", (SOURCE, b))
            log.info("watermark moved to %s", b)
    return batches


def default_pg_connect():
    import psycopg2  # PGHOST / PGPORT / PGUSER / PGPASSWORD from the environment

    return psycopg2.connect(dbname=os.environ.get("PGDATABASE", "project_source"))
