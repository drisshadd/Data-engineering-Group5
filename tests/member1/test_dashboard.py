"""Dashboard verified against known data: on the expected gold sample, the KPI tiles must show the
totals of expected_totals.json (OTP 61/853, net revenue £1,788,710, UK261 £419,540)."""
import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[2] / "dashboard" / "app.py"
EXP = json.loads((APP.parent / "sample_data" / "expected_totals.json").read_text())


def test_dashboard_renders_and_kpis_match_expected_totals():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception, at.exception
    m = {x.label: x.value for x in at.metric}
    assert m["Flights operated"] == f"{EXP['silver_flights']:,}"
    assert m["On-time (OTP15)"] == f"{100 * EXP['gold_on_time_flights'] / EXP['gold_flights_with_delay']:.1f} %"
    assert m["Net revenue"] == f"£{float(EXP['gold_net_revenue_gbp']):,.0f}"
    assert m["UK261 exposure"] == f"£{float(EXP['gold_uk261_exposure_gbp']):,.0f}"
    assert len(at.tabs) == 2


def test_airport_filter_reduces_flights():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    at.multiselect[0].select(at.multiselect[0].options[0]).run()
    assert not at.exception
    n = int(next(x.value for x in at.metric if x.label == "Flights operated").replace(",", ""))
    assert 0 < n < EXP["silver_flights"]
