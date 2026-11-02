"""Bronze profile for the handover to Member 2: what is really in each raw column.
Runs on the generator files (= exactly what bronze holds). Output: docs/member1/bronze_profile.md
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

MISSING = {"", "N/A", "NULL", "null", "-"}
CHECKS = {   # expected shape of a clean value, per column (anything else is "to clean" for M2)
    "airport_code": r"AP[0-9]{3}", "runways": r"[0-9]+", "passenger_id": r"[0-9]+", "flight_id": r"[0-9]+",
    "booking_id": r"[0-9]+", "origin": r"AP[0-9]{3}", "destination": r"AP[0-9]{3}", "seats": r"[0-9]+",
    "delay_min": r"[0-9]+", "fare_gbp": r"[0-9]+\.[0-9]{1,2}", "flight_number": r"SH[0-9]{3}",
    "scheduled_departure": r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]{8}Z", "booked_at": r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]{8}Z",
    "booked_at_v2": r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]{8}Z", "email": r"[^@\sA-Z]+@[^@\sA-Z]+\.[a-z]{2,}",
    "frequent_flyer_tier": r"none|silver|gold|platinum", "cabin": r"economy|premium|business",
}


def profile(data_dir: Path) -> dict:
    tables = {}
    for folder in sorted(Path(data_dir).glob("batch_*")):
        for f in sorted(folder.glob("*.csv")):
            with open(f, newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            t = tables.setdefault(f.stem, {"rows": 0, "files": [], "columns": {}})
            t["rows"] += len(rows)
            t["files"].append(f"{folder.name}/{f.name} ({len(rows)} rows)")
            for col in rows[0].keys() if rows else []:
                c = t["columns"].setdefault(col, {"missing": 0, "bad_shape": 0, "values": Counter(), "examples_bad": Counter(),
                                                 "first_seen": folder.name})
                for r in rows:
                    v = r.get(col) or ""
                    if v.strip() in MISSING:
                        c["missing"] += 1
                        continue
                    c["values"][v] += 1
                    pat = CHECKS.get(col)
                    if pat and not re.fullmatch(pat, v):
                        c["bad_shape"] += 1
                        c["examples_bad"][v] += 1
    return tables


def to_markdown(tables: dict, issues: dict | None) -> str:
    out = ["# Bronze profile — SkyHop (generator seed 42, 2 batches)", "",
           "Produced by `python -m skyhop_ingest profile`. *bad shape* = present but not in the clean format "
           "expected for the column → a cleaning rule is needed in silver.", ""]
    for name, t in tables.items():
        out += [f"## {name} — {t['rows']} rows", "", "Files: " + "; ".join(t["files"]), "",
                "| Column | Missing (empty/N/A/null/-) | Bad shape | Distinct | Examples to clean | First seen |",
                "|---|---|---|---|---|---|"]
        for col, c in t["columns"].items():
            ex = ", ".join(f"`{v!r}`" if v != v.strip() else f"`{v}`" for v, _ in c["examples_bad"].most_common(4)) or "—"
            out.append(f"| {col} | {c['missing']} | {c['bad_shape']} | {len(c['values'])} | {ex} | {c['first_seen']} |")
        out.append("")
    if issues:
        out += ["## Issues injected by the generator (ground truth, `issues_report.json`)", "", "| Issue | Count |", "|---|---|"]
        out += [f"| {k} | {v} |" for k, v in issues["issues_injected"].items()]
    return "\n".join(out) + "\n"


def run(data_dir: Path, out_md: Path):
    tables = profile(data_dir)
    rep = Path(data_dir) / "issues_report.json"
    issues = json.loads(rep.read_text()) if rep.exists() else None
    Path(out_md).write_text(to_markdown(tables, issues), encoding="utf-8")
    return tables
