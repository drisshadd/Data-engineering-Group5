"""API validators: a good answer passes, a wrong 200 answer is rejected (never loaded into bronze)."""
import copy
import json
from pathlib import Path

import pytest
import requests

from skyhop_ingest import apis, cli

FX = Path(__file__).parent / "fixtures" / "api"
load = lambda n: json.loads((FX / n).read_text(encoding="utf-8"))  # noqa: E731


def test_open_meteo_ok_and_broken():
    j = load("open_meteo_london_sept.json")
    assert apis.validate_open_meteo(j, "2026-09-01", "2026-09-30") == 30
    with pytest.raises(apis.ValidationError):                 # API returned fewer days than asked
        apis.validate_open_meteo(j, "2026-09-01", "2026-10-31")
    bad = copy.deepcopy(j)
    bad["daily"]["precipitation_sum"] = [None] * 30            # 200 OK but empty values
    with pytest.raises(apis.ValidationError):
        apis.validate_open_meteo(bad, "2026-09-01", "2026-09-30")


def test_frankfurter_ok_and_broken():
    j = load("frankfurter_sept.json")
    assert apis.validate_frankfurter(j) == 22                  # business days of Sept 2026
    with pytest.raises(apis.ValidationError):
        apis.validate_frankfurter({**j, "base": "GBP"})
    with pytest.raises(apis.ValidationError):
        apis.validate_frankfurter({**j, "rates": {"2026-09-01": {"GBP": 86.0}}})   # x100 rate


def test_govuk_and_nager():
    assert apis.validate_govuk(load("govuk_bank_holidays.json"), 2026) == 27
    with pytest.raises(apis.ValidationError):
        apis.validate_govuk(load("govuk_bank_holidays.json"), 2031)   # year not published yet
    assert apis.validate_nager(load("nager_fr_2026.json"), 2026) == 11
    with pytest.raises(apis.ValidationError):
        apis.validate_nager([], 2026)


def test_ourairports_filters_and_detects_missing():
    text = (FX / "ourairports_sample.csv").read_text()
    rows = apis.parse_ourairports(text, {"LHR", "CDG"})
    assert {r["iata_code"] for r in rows} == {"LHR", "CDG"}
    with pytest.raises(apis.ValidationError):
        apis.parse_ourairports(text, {"LHR", "JFK"})


class Resp:
    def __init__(self, js=None, text=""):
        self._js, self.text = js, text

    def json(self):
        return self._js


def fake_get_factory(down=()):
    def get(url, params=None, **k):
        if any(d in url for d in down):
            raise requests.ConnectionError(f"{url} unreachable")
        if "open-meteo" in url:
            j = load("open_meteo_london_sept.json")
            days = [d for d in j["daily"]["time"]]
            # answer for the requested window
            import datetime as dt
            s, e = dt.date.fromisoformat(params["start_date"]), dt.date.fromisoformat(params["end_date"])
            n = (e - s).days + 1
            t = [(s + dt.timedelta(i)).isoformat() for i in range(n)]
            return Resp({"daily": {"time": t, "precipitation_sum": [0.5] * n, "wind_speed_10m_max": [20.0] * n,
                                   "temperature_2m_max": [15.0] * n}})
        if "frankfurter" in url:
            return Resp(load("frankfurter_sept.json"))
        if "gov.uk" in url:
            return Resp(load("govuk_bank_holidays.json"))
        if "nager" in url:
            return Resp(load("nager_fr_2026.json"))
        if "ourairports" in url:
            return Resp(text=(FX / "ourairports_sample.csv").read_text())
        raise AssertionError(url)
    return get


def test_collect_all_sources_ok():
    results, report = cli.collect_apis("2026-09-01", "2026-09-30", get=fake_get_factory())
    assert all(r["status"] == "OK" for r in report)
    sources = [r[0] for r in results]
    assert sources.count("open_meteo") == 12 and sources.count("ourairports") == 12
    keys = [(r[0], r[2]) for r in results]
    assert len(keys) == len(set(keys))                         # request_key unique -> MERGE idempotent


def test_incident_c_api_outage_others_still_loaded():
    """Incident C (tested): Frankfurter down -> reported FAILED, the 4 other sources are still collected."""
    results, report = cli.collect_apis("2026-09-01", "2026-09-30", outage="frankfurter",
                                       get=fake_get_factory(down=(apis.OUTAGE_HOST,)))
    status = {r["source"]: r["status"] for r in report}
    assert status.pop("frankfurter") == "FAILED"
    assert set(status.values()) == {"OK"}
    assert "frankfurter" not in {r[0] for r in results}


def test_http_get_retries_three_times_then_raises(monkeypatch):
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise requests.Timeout("slow")

    monkeypatch.setattr(apis.requests, "get", boom)
    with pytest.raises(requests.Timeout):
        apis.http_get("https://example.org", sleep=lambda s: None)
    assert len(calls) == 3
