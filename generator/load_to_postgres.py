"""Load the files of messy_data.py into a local PostgreSQL database: your "on-prem" source system.

Every column is loaded as TEXT (a real legacy system is often like that), in a schema named after the company.
Then ingest it into Snowflake or BigQuery like in the ingestion lab (CSV export + COPY, or a Python incremental job).

  pip install psycopg2-binary==2.9.10
  python messy_data.py --company freshroute --batches 2
  python load_to_postgres.py --company freshroute --batch 1                  # tables freshroute.<table>
  python load_to_postgres.py --company freshroute --batch 2 --append         # next day: append batch 2

Connection: standard PG* environment variables (PGHOST, PGPORT, PGUSER, PGPASSWORD), database --db (created if needed).
"""
import argparse
import csv
from pathlib import Path

import psycopg2
from psycopg2 import sql


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--company", required=True)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--data", default="out", help="folder written by messy_data.py")
    ap.add_argument("--db", default="project_source")
    ap.add_argument("--append", action="store_true", help="keep existing rows (next batch) instead of recreating tables")
    a = ap.parse_args()

    folder = Path(a.data) / a.company / f"batch_{a.batch:03d}"
    files = sorted(folder.glob("*.csv"))
    if not files:
        raise SystemExit(f"No CSV in {folder}: run messy_data.py first (JSON lines are not supported here).")

    # CREATE DATABASE cannot run inside a transaction: plain connection in autocommit mode
    admin = psycopg2.connect(dbname="postgres")
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (a.db,))
        if not cur.fetchone():
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(a.db)))
            print(f"Created database {a.db}")
    admin.close()

    with psycopg2.connect(dbname=a.db) as con, con.cursor() as cur:
        cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(a.company)))
        for f in files:
            table = sql.Identifier(a.company, f.stem)
            with open(f, newline="", encoding="utf-8") as fh:
                header = next(csv.reader(fh))
            cols = header + ["_batch", "_loaded_at"]
            if not a.append:
                cur.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(table))
            cur.execute(sql.SQL("CREATE TABLE IF NOT EXISTS {} ({}, _batch int, _loaded_at timestamptz DEFAULT now())").format(
                table, sql.SQL(", ").join(sql.SQL("{} text").format(sql.Identifier(c)) for c in header)))
            # schema drift (batch 2+): add any new column instead of failing
            for c in header:
                cur.execute(sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS {} text").format(table, sql.Identifier(c)))
            with open(f, encoding="utf-8") as fh:
                cur.copy_expert(sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true)").format(
                    table, sql.SQL(", ").join(map(sql.Identifier, header))), fh)
            cur.execute(sql.SQL("UPDATE {} SET _batch = %s WHERE _batch IS NULL").format(table), (a.batch,))
            cur.execute(sql.SQL("SELECT count(*) FROM {}").format(table))
            print(f"{a.company}.{f.stem:16} {cur.fetchone()[0]:>7} rows (batch {a.batch} loaded)")
    con.close()


if __name__ == "__main__":
    main()
