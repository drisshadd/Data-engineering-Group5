"""Public APIs used by SkyHop (no key, no payment) + a validator per API.

Every call: timeout, 3 attempts with back-off, raise_for_status (fail loudly). Every response is VALIDATED
before it is written to bronze: a 200 with a wrong body is an error too.

| Source       | What                                   | Used for                                  |
|--------------|----------------------------------------|-------------------------------------------|
| Open-Meteo   | daily weather archive per city         | UC1 context: delays vs rain / wind        |
| Frankfurter  | ECB EUR->GBP rates                     | UC2 EUR view for the Paris / Lyon stations |
| GOV.UK       | UK bank holidays (3 divisions)         | UC1/UC2 calendar effects                  |
| Nager.Date   | French public holidays                 | idem for Paris / Lyon                     |
| OurAirports  | real airport reference (CSV)           | check of the city -> IATA reference       |
"""
from __future__ import annotations

import csv
import io
import logging
import time
from datetime import date

import requests

log = logging.getLogger("skyhop.apis")
UA = {"User-Agent": "skyhop-student-project/1.0 (data engineering course)"}

OPEN_METEO = "https://archive-api.open-meteo.com/v1/archive"
FRANKFURTER = "https://api.frankfurter.dev/v1/{start}..{end}"
GOVUK = "https://www.gov.uk/bank-holidays.json"
NAGER = "https://date.nager.at/api/v3/PublicHolidays/{year}/FR"
OURAIRPORTS = "https://davidmegginson.github.io/ourairports-data/airports.csv"

# incident C rehearsal: --simulate-outage frankfurter points the call to a host that does not exist
OUTAGE_HOST = "https://outage.invalid"


class ValidationError(Exception):
    """The API answered, but not what we expect: never load it into bronze."""


def http_get(url, params=None, retries=3, timeout=30, sleep=time.sleep):
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers=UA)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            log.warning("GET %s failed (attempt %d/%d): %s", url, attempt, retries, e)
            if attempt == retries:
                raise
            sleep(2 ** attempt)


# --------------------------------------------------------------------------------------- validators
def _require(cond, msg):
    if not cond:
        raise ValidationError(msg)


def validate_open_meteo(j: dict, start: str, end: str) -> int:
    d = j.get("daily") or {}
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    _require("time" in d, "open-meteo: no daily.time")
    _require(len(d["time"]) == days, f"open-meteo: {len(d['time'])} days instead of {days}")
    _require(d["time"][0] == start and d["time"][-1] == end, "open-meteo: wrong date range")
    for k in ("precipitation_sum", "wind_speed_10m_max", "temperature_2m_max"):
        _require(k in d and len(d[k]) == days, f"open-meteo: {k} missing or wrong length")
    nulls = sum(v is None for k in ("precipitation_sum", "wind_speed_10m_max") for v in d[k])
    _require(nulls <= days // 10, f"open-meteo: {nulls} null values")
    return days


def validate_frankfurter(j: dict) -> int:
    _require(j.get("base") == "EUR", f"frankfurter: base {j.get('base')} instead of EUR")
    rates = j.get("rates") or {}
    _require(len(rates) > 0, "frankfurter: no rate")
    for day, v in rates.items():
        date.fromisoformat(day)
        _require(0.6 < float(v.get("GBP", 0)) < 1.1, f"frankfurter: implausible GBP rate {v} on {day}")
    return len(rates)


def validate_govuk(j: dict, year: int) -> int:
    divisions = {"england-and-wales", "scotland", "northern-ireland"}
    _require(divisions <= set(j), f"gov.uk: divisions {sorted(j)}")
    n = 0
    for dv in divisions:
        events = j[dv].get("events") or []
        in_year = [e for e in events if str(e.get("date", "")).startswith(str(year))]
        _require(len(in_year) >= 7, f"gov.uk: only {len(in_year)} {dv} holidays in {year}")
        n += len(in_year)
    return n


def validate_nager(j: list, year: int) -> int:
    _require(isinstance(j, list) and len(j) >= 10, "nager: fewer than 10 French holidays")
    for h in j:
        _require(str(h.get("date", "")).startswith(str(year)), f"nager: date {h.get('date')} outside {year}")
        _require(h.get("countryCode") == "FR", "nager: countryCode is not FR")
    return len(j)


def parse_ourairports(text: str, wanted: set[str]) -> list[dict]:
    keep = []
    for r in csv.DictReader(io.StringIO(text)):
        if r.get("iata_code") in wanted:
            keep.append({"iata_code": r["iata_code"], "name": r["name"], "municipality": r.get("municipality"),
                         "iso_country": r.get("iso_country"), "latitude_deg": float(r["latitude_deg"]),
                         "longitude_deg": float(r["longitude_deg"]), "type": r.get("type")})
    missing = wanted - {k["iata_code"] for k in keep}
    _require(not missing, f"ourairports: IATA not found {sorted(missing)}")
    return keep


# ------------------------------------------------------------------------------------------ fetchers
# Each returns a list of (source, entity, request_key, payload, n_records). request_key makes the MERGE idempotent.
def fetch_open_meteo(cities: list[dict], start: str, end: str, get=http_get):
    out = []
    for c in cities:
        j = get(OPEN_METEO, params={"latitude": c["latitude"], "longitude": c["longitude"], "start_date": start,
                                    "end_date": end, "timezone": "Europe/London",
                                    "daily": "precipitation_sum,wind_speed_10m_max,temperature_2m_max"}).json()
        n = validate_open_meteo(j, start, end)
        out.append(("open_meteo", c["city"], f"{c['city']}|{start}|{end}", j, n))
    return out


def fetch_frankfurter(start: str, end: str, get=http_get, outage=False):
    url = FRANKFURTER.format(start=start, end=end)
    if outage:
        url = url.replace("https://api.frankfurter.dev", OUTAGE_HOST)
    j = get(url, params={"from": "EUR", "to": "GBP"}).json()
    return [("frankfurter", "EURGBP", f"EURGBP|{start}|{end}", j, validate_frankfurter(j))]


def fetch_govuk(year: int, get=http_get):
    j = get(GOVUK).json()
    return [("govuk_bank_holidays", "GB", "bank-holidays", j, validate_govuk(j, year))]


def fetch_nager(years: list[int], get=http_get):
    out = []
    for y in years:
        j = get(NAGER.format(year=y)).json()
        out.append(("nager_date", "FR", f"FR|{y}", j, validate_nager(j, y)))
    return out


def fetch_ourairports(wanted: set[str], get=http_get):
    rows = parse_ourairports(get(OURAIRPORTS, timeout=60).text, wanted)
    return [("ourairports", r["iata_code"], r["iata_code"], r, 1) for r in rows]
