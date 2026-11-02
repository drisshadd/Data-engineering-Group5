"""SkyHop ingestion CLI (Member 1). One command = one Airflow task (Member 3 plugs them into the DAG).

  generate      run the course generator (seed 42, 2 batches) + write expected bronze counts
  check-apis    call the 5 public APIs, validate the answers, write docs/member1/api_check_report.md
  profile       bronze profile for Member 2 (docs/member1/bronze_profile.md)
  files         source 1: flight-ops CSV files       -> stage -> BRONZE.FLIGHTS / AIRPORTS
  postgres      source 2: reservation DB (watermark) -> stage -> BRONZE.BOOKINGS / PASSENGERS
  reservations-files   fallback for source 2 when PostgreSQL is not available (same stage path)
  apis          sources 3-7: public APIs             -> BRONZE.API_RAW (MERGE)
  verify        bronze row counts per file == expected counts (exit 1 if not)

Exit code 0 = success, 1 = at least one source failed (Airflow marks the task failed and retries).
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import apis, bronze, postgres_extract
from . import profile as prof

ROOT = Path(__file__).resolve().parents[2]
log = logging.getLogger("skyhop.cli")


def cities(ref=ROOT / "reference" / "city_reference.csv"):
    with open(ref, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def years(start, end):
    return list(range(int(start[:4]), int(end[:4]) + 1))


def collect_apis(start, end, outage=None, get=apis.http_get):
    """Fetch + validate all sources. One failing source never stops the others."""
    ref = cities()
    jobs = [
        ("ourairports", lambda: apis.fetch_ourairports({c["iata"] for c in ref}, get=get)),
        ("open_meteo", lambda: apis.fetch_open_meteo(ref, start, end, get=get)),
        ("frankfurter", lambda: apis.fetch_frankfurter(start, end, get=get, outage=(outage == "frankfurter"))),
        ("govuk_bank_holidays", lambda: apis.fetch_govuk(int(end[:4]), get=get)),
        ("nager_date", lambda: apis.fetch_nager(years(start, end), get=get)),
    ]
    results, report = [], []
    for name, fn in jobs:
        t0 = time.perf_counter()
        try:
            got = fn()
            results += got
            report.append({"source": name, "status": "OK", "requests": len(got),
                           "records": sum(g[4] for g in got), "seconds": round(time.perf_counter() - t0, 2), "error": ""})
        except Exception as e:  # noqa: BLE001
            log.error("%s FAILED: %s", name, e)
            report.append({"source": name, "status": "FAILED", "requests": 0, "records": 0,
                           "seconds": round(time.perf_counter() - t0, 2), "error": f"{type(e).__name__}: {e}"[:160]})
    return results, report


def write_api_report(report, start, end, path=ROOT / "docs" / "member1" / "api_check_report.md"):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# API check — {now}", "", f"Window {start} → {end}. Validation rules: `ingestion/skyhop_ingest/apis.py`.", "",
             "| Source | Status | Requests | Records validated | Seconds | Error |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['source']} | {r['status']} | {r['requests']} | {r['records']} | {r['seconds']} | {r['error']} |" for r in report]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(prog="skyhop_ingest", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["generate", "check-apis", "profile", "files", "postgres", "reservations-files",
                                        "apis", "verify"])
    ap.add_argument("--data", default=str(ROOT / "generator" / "out" / "skyhop"))
    ap.add_argument("--batch", type=int, default=1, help="batch / day number (Airflow passes it)")
    ap.add_argument("--as-batch", type=int, help="upload under another batch number (incident rehearsal)")
    ap.add_argument("--start", default="2026-06-01", help="API window start (bookings start 1 June)")
    ap.add_argument("--end", default="2026-09-30", help="API window end (last flight 30 Sept)")
    ap.add_argument("--simulate-outage", choices=["frankfurter"], help="incident C rehearsal")
    a = ap.parse_args(argv)
    data = Path(a.data)
    exp_file = ROOT / "docs" / "member1" / "bronze_expected_counts.json"

    if a.command == "generate":
        out = data.parent
        subprocess.run([sys.executable, str(ROOT / "generator" / "messy_data.py"), "--company", "skyhop",
                        "--batches", "2", "--seed", "42", "--out", str(out)], check=True)
        exp = bronze.expected_counts(data)
        exp_file.write_text(json.dumps(exp, indent=2))
        print(json.dumps(exp, indent=2), f"\ntotal rows: {sum(exp.values())}")
        return 0
    if a.command == "profile":
        prof.run(data, ROOT / "docs" / "member1" / "bronze_profile.md")
        print("written docs/member1/bronze_profile.md")
        return 0
    if a.command == "check-apis":
        _, report = collect_apis(a.start, a.end, a.simulate_outage)
        write_api_report(report, a.start, a.end)
        return 1 if any(r["status"] != "OK" for r in report) else 0

    con = bronze.connect()
    try:
        cur = con.cursor()
        if a.command == "files":
            bronze.load_files(cur, data, a.batch, ("flights", "airports"), a.as_batch)
        elif a.command == "reservations-files":
            bronze.load_files(cur, data, a.batch, ("passengers", "bookings"), a.as_batch)
        elif a.command == "postgres":
            postgres_extract.extract(cur, postgres_extract.default_pg_connect)
        elif a.command == "apis":
            results, report = collect_apis(a.start, a.end, a.simulate_outage)
            for source, entity, key, payload, _ in results:
                bronze.merge_api(cur, source, entity, key, payload)
            log.info("API_RAW: %d documents merged", len(results))
            failed = [r["source"] for r in report if r["status"] != "OK"]
            if failed:
                log.error("sources failed: %s (others loaded)", failed)
                return 1
        elif a.command == "verify":
            rep = bronze.verify(cur, json.loads(exp_file.read_text()))
            print(f"{'file':48} {'expected':>9} {'bronze':>9}  status")
            for k, e, n, s in rep:
                print(f"{k:48} {str(e):>9} {str(n):>9}  {s}")
            cur.execute("SELECT source, COUNT(*) FROM SKYHOP.BRONZE.API_RAW GROUP BY 1 ORDER BY 1")
            print("API_RAW:", cur.fetchall())
            return 0 if all(s == "OK" for *_, s in rep) else 1
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
