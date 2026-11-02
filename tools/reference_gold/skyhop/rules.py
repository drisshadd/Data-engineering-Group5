"""SkyHop cleaning rules - ONE definition of "how we read a messy value".

These pure functions are the executable specification of the silver layer.
snowflake/02_functions.sql implements exactly the same rules in SQL; the reconciliation
query (snowflake/09_reconciliation.sql) proves both give the same gold numbers.
Standard library only.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")
MISSING_MARKERS = {"", "N/A", "NULL", "-"}

# Business thresholds (documented in docs/01_business_case.md)
PENCE_THRESHOLD_GBP = Decimal("1000")   # max real fare is ~420 GBP; x100 errors start at 2,900
DELAY_MIN, DELAY_MAX = 0, 1440          # a delay is between 0 min and 24 h
SEATS_MIN, SEATS_MAX = 50, 400          # SkyHop fleet: 70-190 seats
ON_TIME_THRESHOLD_MIN = 15              # industry OTP15 definition
UK261_DELAY_MIN = 180                   # 3 h delay -> compensation is due
UK261_SHORT_HAUL_GBP = Decimal("220")   # <= 1,500 km flights


def clean_text(v: str | None) -> str | None:
    if v is None:
        return None
    t = v.strip()
    return None if t.upper() in MISSING_MARKERS else t


def parse_int(v: str | None) -> int | None:
    t = clean_text(v)
    if t is None:
        return None
    m = re.search(r"-?[0-9]+", t)
    return int(m.group(0)) if m else None


def parse_money(v: str | None) -> tuple[Decimal | None, str | None]:
    """Return (amount, currency). '£12.50', '12.50 GBP', '12,50', ' 12.5 ' -> GBP.
    '€12.50' -> currency 'EUR' and amount None (we never guess a currency)."""
    t = clean_text(v)
    if t is None:
        return None, None
    if "€" in t:
        return None, "EUR"
    t = t.replace("£", "").replace("GBP", "").replace(" ", "")
    if re.fullmatch(r"-?[0-9]+,[0-9]{1,2}", t):
        t = t.replace(",", ".")
    else:
        t = t.replace(",", "")
    if not re.fullmatch(r"-?[0-9]+(\.[0-9]+)?", t):
        return None, "GBP"
    try:
        return Decimal(t).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "GBP"
    except InvalidOperation:
        return None, "GBP"


def parse_ts(v: str | None) -> datetime | None:
    """ISO with Z or offset, 'yyyy-mm-dd hh:mi:ss' (UTC), epoch seconds, 'dd/mm/yyyy hh:mi' (UTC).
    Returns an aware UTC datetime. 1970 / 2099 are default values -> None."""
    t = clean_text(v)
    if t is None:
        return None
    dt = None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            dt = datetime.strptime(t.replace("Z", "+00:00") if fmt.endswith("%z") else t, fmt)
            break
        except ValueError:
            continue
    if dt is None and re.fullmatch(r"[0-9]{9,10}", t):
        dt = datetime.fromtimestamp(int(t), tz=timezone.utc)
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return None if dt.year in (1970, 2099) else dt


def london_date(dt: datetime | None):
    return dt.astimezone(LONDON).date() if dt else None


def norm_cabin(v: str | None) -> str | None:
    t = clean_text(v)
    if t is None:
        return None
    t = t.lower()
    for prefix, value in (("econ", "economy"), ("prem", "premium"), ("bus", "business")):
        if t.startswith(prefix):
            return value
    return None


def norm_tier(v: str | None) -> str | None:
    t = clean_text(v)
    if t is None:
        return None
    t = t.lower()
    for prefix, value in (("none", "none"), ("silver", "silver"), ("gold", "gold"), ("plat", "platinum")):
        if t.startswith(prefix):
            return value
    return None


def norm_code(v: str | None) -> str | None:
    t = clean_text(v)
    return t.upper() if t else None


def norm_email(v: str | None) -> str | None:
    t = clean_text(v)
    if t is None:
        return None
    t = t.lower().replace(" ", "")
    if t == "test@test.com" or ".." in t or not re.fullmatch(r"[^@]+@[^@]+\.[a-z]{2,}", t):
        return None
    return t


def initcap(v: str | None) -> str | None:
    """Same behaviour as Snowflake INITCAP for simple words: 'lONDON ' -> 'London'."""
    t = clean_text(v)
    if t is None:
        return None
    return re.sub(r"[A-Za-z]+", lambda m: m.group(0)[0].upper() + m.group(0)[1:].lower(), t)


def fare_gbp(amount: Decimal | None) -> Decimal | None:
    if amount is None:
        return None
    a = abs(amount)
    return (a / 100).quantize(Decimal("0.01")) if a >= PENCE_THRESHOLD_GBP else a
