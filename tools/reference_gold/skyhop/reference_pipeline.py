"""Local reference implementation of bronze -> silver -> gold (no cloud, standard library only).

Why it exists:
  1. Unit-testable specification of every business rule (pytest, CI).
  2. "Known data" check: on a hand-made fixture we know the right answer; on the generator data
     it gives the expected totals that Snowflake must reproduce (snowflake/09_reconciliation.sql).

  python -m skyhop.reference_pipeline --data generator/out/skyhop --out reference/expected
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from skyhop import rules as R

TABLES = ("airports", "passengers", "flights", "bookings")


def ratio(num, den, places):
    """ROUND(num / den, places) with Snowflake semantics (half away from zero); None when den = 0."""
    if not den:
        return None
    return str((Decimal(num) / Decimal(den)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


# ----------------------------------------------------------------------------------------- bronze
def load_bronze(data_dir: Path) -> dict[str, list[dict]]:
    """Every batch folder, every column as text, plus _batch and _source_file (= bronze)."""
    bronze = {t: [] for t in TABLES}
    for folder in sorted(Path(data_dir).glob("batch_*")):
        batch = int(re.search(r"batch_(\d+)", folder.name).group(1))
        for t in TABLES:
            f = folder / f"{t}.csv"
            if not f.exists():
                continue
            with open(f, newline="", encoding="utf-8") as fh:
                for i, row in enumerate(csv.DictReader(fh)):
                    row = {k: (v if v != "" else None) for k, v in row.items()}
                    row["_batch"], row["_source_file"], row["_row"] = batch, f"batch_{batch:03d}/{t}.csv", i
                    bronze[t].append(row)
    return bronze


def _sortable(v):
    """NULLS LAST, then plain string order (same as Snowflake ORDER BY ... ASC)."""
    return (1, "") if v is None else (0, v)


def _pick_latest(rows, key, score, raw_cols):
    """One row per key: latest batch wins, then fewest problems, then a deterministic raw-value order."""
    best = {}
    for r in rows:
        k = key(r)
        if k is None:
            continue
        rank = (-r["_batch"], score(r), *[_sortable(r.get(c)) for c in raw_cols])
        if k not in best or rank < best[k][0]:
            best[k] = (rank, r)
    return [r for _, r in best.values()]


# ----------------------------------------------------------------------------------------- silver
def build_silver(bronze):
    s = {}
    # airports -------------------------------------------------------------------------------
    rows = []
    for r in bronze["airports"]:
        rows.append({"airport_code": R.norm_code(r.get("airport_code")), "city": R.initcap(r.get("city")),
                     "runways": R.parse_int(r.get("runways")), "_batch": r["_batch"],
                     "city_raw": r.get("city"), "runways_raw": r.get("runways")})
    s["airports"] = _pick_latest(rows, lambda x: x["airport_code"],
                                 lambda x: (x["city"] is None) + (x["runways"] is None),
                                 ["city_raw", "runways_raw"])
    s["airports"] = sorted(s["airports"], key=lambda x: x["airport_code"])
    known_airports = {a["airport_code"]: a for a in s["airports"]}

    # passengers (PII: masked in Snowflake) -------------------------------------------------------
    rows = []
    for r in bronze["passengers"]:
        pid = R.parse_int(r.get("passenger_id"))
        rows.append({"passenger_id": pid, "email": R.norm_email(r.get("email")),
                     "tier": R.norm_tier(r.get("frequent_flyer_tier")), "_batch": r["_batch"],
                     "full_name": r.get("full_name"), "email_raw": r.get("email"),
                     "tier_raw": r.get("frequent_flyer_tier")})
    s["passengers"] = _pick_latest(rows, lambda x: x["passenger_id"],
                                   lambda x: (x["email"] is None) + (x["tier"] is None),
                                   ["email_raw", "tier_raw", "full_name"])
    known_pax = {p["passenger_id"] for p in s["passengers"]}

    # flights --------------------------------------------------------------------------------------
    typed = []
    for r in bronze["flights"]:
        fid = R.parse_int(r.get("flight_id"))
        o, d = R.norm_code(r.get("origin")), R.norm_code(r.get("destination"))
        dep = R.parse_ts(r.get("scheduled_departure"))
        delay, seats = R.parse_int(r.get("delay_min")), R.parse_int(r.get("seats"))
        problems = []
        if fid is None:
            problems.append("missing flight_id")
        if o not in known_airports:
            problems.append("unknown origin")
        if d not in known_airports:
            problems.append("unknown destination")
        if o is not None and o == d:
            problems.append("origin equals destination")
        if dep is None:
            problems.append("scheduled_departure not readable")
        flags = []
        if delay is None or not (R.DELAY_MIN <= delay <= R.DELAY_MAX):
            flags.append("delay missing or out of range")
            delay = None
        if seats is None or not (R.SEATS_MIN <= seats <= R.SEATS_MAX):
            flags.append("seats missing or out of range")
            seats = None
        typed.append({**r, "flight_id_n": fid, "origin_n": o, "destination_n": d, "dep": dep, "delay": delay,
                      "seats_n": seats, "flight_number_n": R.norm_code(r.get("flight_number")),
                      "problems": problems, "flags": flags})
    winners = _pick_latest(typed, lambda x: x["flight_id_n"], lambda x: len(x["problems"]) + len(x["flags"]),
                           ["scheduled_departure", "delay_min", "seats", "origin", "destination", "flight_number"])
    s["flights"] = sorted([w for w in winners if not w["problems"]], key=lambda x: x["flight_id_n"])
    s["flights_quarantine"] = [w for w in winners if w["problems"]] + [t for t in typed if t["flight_id_n"] is None]
    s["flights_dup_removed"] = len(bronze["flights"]) - len(winners) - sum(t["flight_id_n"] is None for t in typed)
    known_flights = {f["flight_id_n"] for f in s["flights"]}

    # bookings -------------------------------------------------------------------------------------
    typed = []
    for r in bronze["bookings"]:
        bid = R.parse_int(r.get("booking_id"))
        fl = R.parse_int(r.get("flight_id"))
        pax = R.parse_int(r.get("passenger_id"))
        amount, cur = R.parse_money(r.get("fare_gbp"))
        booked_raw = r.get("booked_at") if r.get("booked_at") is not None else r.get("booked_at_v2")  # schema drift
        problems = []
        if bid is None:
            problems.append("missing booking_id")
        if fl not in known_flights:
            problems.append("unknown or quarantined flight_id")
        if cur == "EUR":
            problems.append("fare in EUR on a GBP feed")
        elif amount is None:
            problems.append("fare not readable")
        flags = []
        if pax not in known_pax:
            flags.append("unknown passenger")
            pax = None
        cabin = R.norm_cabin(r.get("cabin"))
        if cabin is None:
            flags.append("cabin unknown")
        booked = R.parse_ts(booked_raw)
        if booked is None:
            flags.append("booked_at not readable")
        typed.append({**r, "booking_id_n": bid, "flight_id_n": fl, "passenger_id_n": pax, "amount": amount,
                      "cabin_n": cabin, "booked": booked, "booked_raw": booked_raw,
                      "problems": problems, "flags": flags})
    winners = _pick_latest(typed, lambda x: x["booking_id_n"], lambda x: len(x["problems"]) + len(x["flags"]),
                           ["fare_gbp", "flight_id", "passenger_id", "cabin", "booked_raw"])
    s["bookings"] = sorted([w for w in winners if not w["problems"]], key=lambda x: x["booking_id_n"])
    s["bookings_quarantine"] = [w for w in winners if w["problems"]] + [t for t in typed if t["booking_id_n"] is None]
    s["bookings_dup_removed"] = len(bronze["bookings"]) - len(winners) - sum(t["booking_id_n"] is None for t in typed)
    for b in s["bookings"]:
        b["is_refund"] = b["amount"] < 0
        b["fare"] = R.fare_gbp(b["amount"])
    return s


# ------------------------------------------------------------------------------------------- gold
def build_gold(s):
    airports = {a["airport_code"]: a for a in s["airports"]}
    # UC1 - daily on-time performance per origin airport (London business day)
    otp = defaultdict(lambda: {"flights": 0, "with_delay": 0, "on_time": 0, "delay_sum": 0, "delayed_3h": 0})
    for f in s["flights"]:
        g = otp[(R.london_date(f["dep"]).isoformat(), f["origin_n"])]
        g["flights"] += 1
        if f["delay"] is not None:
            g["with_delay"] += 1
            g["delay_sum"] += f["delay"]
            g["on_time"] += f["delay"] <= R.ON_TIME_THRESHOLD_MIN
            g["delayed_3h"] += f["delay"] >= R.UK261_DELAY_MIN
    daily_otp = []
    for (day, origin), g in sorted(otp.items()):
        daily_otp.append({
            "business_date": day, "origin_airport": origin, "origin_city": airports[origin]["city"],
            "flights_operated": g["flights"], "flights_with_delay": g["with_delay"], "on_time_flights": g["on_time"],
            "otp15_pct": ratio(100 * g["on_time"], g["with_delay"], 2),
            "avg_delay_min": ratio(g["delay_sum"], g["with_delay"], 1),
            "flights_delayed_3h_plus": g["delayed_3h"]})

    # UC2 - revenue and direct-channel load factor per flight
    per_flight = defaultdict(lambda: {"sold": 0, "refunds": 0, "net": Decimal("0"), "refunded": Decimal("0")})
    for b in s["bookings"]:
        p = per_flight[b["flight_id_n"]]
        if b["is_refund"]:
            p["refunds"] += 1
            p["refunded"] += b["fare"]
        else:
            p["sold"] += 1
            p["net"] += b["fare"]
    flight_perf = []
    for f in s["flights"]:
        p = per_flight[f["flight_id_n"]]
        delayed_3h = f["delay"] is not None and f["delay"] >= R.UK261_DELAY_MIN
        flight_perf.append({
            "flight_id": f["flight_id_n"], "flight_number": f["flight_number_n"],
            "business_date": R.london_date(f["dep"]).isoformat(), "origin_airport": f["origin_n"],
            "destination_airport": f["destination_n"], "seats": f["seats_n"], "delay_min": f["delay"],
            "bookings_sold": p["sold"], "bookings_refunded": p["refunds"],
            "net_revenue_gbp": str(p["net"].quantize(Decimal("0.01"))),
            "refunded_gbp": str(p["refunded"].quantize(Decimal("0.01"))),
            "load_factor_pct": ratio(100 * p["sold"], f["seats_n"], 2),
            "uk261_exposure_gbp": str((R.UK261_SHORT_HAUL_GBP * p["sold"]) if delayed_3h else Decimal("0"))})
    return {"daily_otp": daily_otp, "flight_performance": flight_perf}


def reconciliation(bronze, s, g) -> dict:
    """The totals Snowflake must reproduce (snowflake/09_reconciliation.sql prints the same keys)."""
    fp = g["flight_performance"]
    return {
        "bronze_flights": len(bronze["flights"]), "bronze_bookings": len(bronze["bookings"]),
        "silver_airports": len(s["airports"]), "silver_passengers": len(s["passengers"]),
        "silver_flights": len(s["flights"]), "quarantine_flights": len(s["flights_quarantine"]),
        "duplicates_removed_flights": s["flights_dup_removed"],
        "silver_bookings": len(s["bookings"]), "quarantine_bookings": len(s["bookings_quarantine"]),
        "duplicates_removed_bookings": s["bookings_dup_removed"],
        "gold_daily_otp_rows": len(g["daily_otp"]),
        "gold_on_time_flights": sum(r["on_time_flights"] for r in g["daily_otp"]),
        "gold_flights_with_delay": sum(r["flights_with_delay"] for r in g["daily_otp"]),
        "gold_bookings_sold": sum(r["bookings_sold"] for r in fp),
        "gold_bookings_refunded": sum(r["bookings_refunded"] for r in fp),
        "gold_net_revenue_gbp": str(sum(Decimal(r["net_revenue_gbp"]) for r in fp)),
        "gold_refunded_gbp": str(sum(Decimal(r["refunded_gbp"]) for r in fp)),
        "gold_uk261_exposure_gbp": str(sum(Decimal(r["uk261_exposure_gbp"]) for r in fp)),
    }


def quarantine_reasons(s) -> dict:
    c = Counter()
    for t in ("flights_quarantine", "bookings_quarantine"):
        for r in s[t]:
            for p in r["problems"]:
                c[f"{t.split('_')[0]}: {p}"] += 1
    return dict(c.most_common())


def run(data_dir, out_dir=None):
    bronze = load_bronze(Path(data_dir))
    s = build_silver(bronze)
    g = build_gold(s)
    rec = reconciliation(bronze, s, g)
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        for name, rows in g.items():
            with open(out / f"{name}.csv", "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
        (out / "reconciliation.json").write_text(json.dumps(rec, indent=2))
        (out / "quarantine_reasons.json").write_text(json.dumps(quarantine_reasons(s), indent=2))
    return bronze, s, g, rec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="generator/out/skyhop")
    ap.add_argument("--out", default="reference/expected")
    a = ap.parse_args()
    _, s, _, rec = run(a.data, a.out)
    print(json.dumps(rec, indent=2))
    print(json.dumps(quarantine_reasons(s), indent=2))


if __name__ == "__main__":
    main()
