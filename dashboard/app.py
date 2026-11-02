"""SkyHop · Operations & Revenue dashboard on GOLD (Member 1).

Reads ONLY the two gold tables (contract: dashboard/GOLD_CONTRACT.md). Three ways to run it:
  1. Streamlit in Snowflake (cloud): paste this file in Snowsight > Projects > Streamlit, role SKYHOP_ANALYST.
  2. Laptop on Snowflake:  SKYHOP_DASH_SOURCE=snowflake streamlit run dashboard/app.py   (key-pair, role SKYHOP_ANALYST)
  3. Laptop offline:       streamlit run dashboard/app.py   (dashboard/sample_data = expected gold, seed 42)
"""
from __future__ import annotations

import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

GOLD = os.environ.get("SKYHOP_GOLD_SCHEMA", "SKYHOP.GOLD")
SAMPLE = Path(__file__).parent / "sample_data"
OTP_THRESHOLD_MIN = 15
NAVY, AMBER, RED, GREY = "#0B1F3A", "#F2A541", "#C8553D", "#8FA3BF"

st.set_page_config(page_title="SkyHop · Ops & Revenue", page_icon="✈️", layout="wide")


# ------------------------------------------------------------------------------------------- data
def _snowflake_frames():
    q_otp, q_fp = f"SELECT * FROM {GOLD}.DAILY_OTP", f"SELECT * FROM {GOLD}.FLIGHT_PERFORMANCE"
    try:  # 1. Streamlit in Snowflake
        from snowflake.snowpark.context import get_active_session
        s = get_active_session()
        return s.sql(q_otp).to_pandas(), s.sql(q_fp).to_pandas(), "Snowflake · Streamlit in Snowflake"
    except Exception:  # noqa: BLE001
        pass
    import snowflake.connector  # 2. laptop on Snowflake
    con = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"], user=os.environ["SNOWFLAKE_USER"],
        private_key_file=os.environ["SNOWFLAKE_PRIVATE_KEY_FILE"], role=os.environ.get("SNOWFLAKE_ROLE", "SKYHOP_ANALYST"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "SKYHOP_WH"))
    try:
        cur = con.cursor()
        otp = cur.execute(q_otp).fetch_pandas_all()
        fp = cur.execute(q_fp).fetch_pandas_all()
    finally:
        con.close()
    return otp, fp, f"Snowflake · {GOLD} (role {os.environ.get('SNOWFLAKE_ROLE', 'SKYHOP_ANALYST')})"


@st.cache_data(ttl=600, show_spinner="Reading gold…")
def load(source: str):
    if source == "snowflake" or _in_snowflake():
        otp, fp, label = _snowflake_frames()
    else:
        otp, fp = pd.read_csv(SAMPLE / "daily_otp.csv"), pd.read_csv(SAMPLE / "flight_performance.csv")
        label = "offline sample = expected gold (seed 42, 2 batches)"
    otp.columns, fp.columns = [c.lower() for c in otp.columns], [c.lower() for c in fp.columns]
    for df in (otp, fp):
        df["business_date"] = pd.to_datetime(df["business_date"]).dt.date
    num_otp = ["flights_operated", "flights_with_delay", "on_time_flights", "otp15_pct", "avg_delay_min", "flights_delayed_3h_plus"]
    num_fp = ["seats", "delay_min", "bookings_sold", "bookings_refunded", "net_revenue_gbp", "refunded_gbp",
              "load_factor_pct", "uk261_exposure_gbp"]
    otp[num_otp] = otp[num_otp].apply(pd.to_numeric, errors="coerce")
    fp[num_fp] = fp[num_fp].apply(pd.to_numeric, errors="coerce")
    return otp, fp, label


def _in_snowflake() -> bool:
    try:
        from snowflake.snowpark.context import get_active_session
        get_active_session()
        return True
    except Exception:  # noqa: BLE001
        return False


def kpis(otp: pd.DataFrame, fp: pd.DataFrame) -> dict:
    """All ratios are recomputed from counts (never an average of percentages)."""
    with_delay = otp["flights_with_delay"].sum()
    seats = fp.loc[fp["seats"].notna(), "seats"].sum()
    sold_with_seats = fp.loc[fp["seats"].notna(), "bookings_sold"].sum()
    return {
        "flights": int(otp["flights_operated"].sum()),
        "otp15": 100 * otp["on_time_flights"].sum() / with_delay if with_delay else None,
        "avg_delay": fp["delay_min"].mean() if fp["delay_min"].notna().any() else None,
        "delayed_3h": int(otp["flights_delayed_3h_plus"].sum()),
        "net_revenue": float(fp["net_revenue_gbp"].sum()),
        "load_factor": 100 * sold_with_seats / seats if seats else None,
        "uk261": float(fp["uk261_exposure_gbp"].sum()),
        "refunded": float(fp["refunded_gbp"].sum()),
    }


def fmt(v, kind):
    if v is None or pd.isna(v):
        return "n/a"
    return {"pct": f"{v:.1f} %", "gbp": f"£{v:,.0f}", "min": f"{v:.0f} min", "int": f"{v:,}"}[kind]


# --------------------------------------------------------------------------------------------- UI
source = os.environ.get("SKYHOP_DASH_SOURCE", "csv")
try:
    otp_all, fp_all, label = load(source)
except Exception as e:  # noqa: BLE001 - failure must be visible, not a blank page
    st.error(f"Gold tables not readable ({type(e).__name__}). Check the role (SKYHOP_ANALYST) and that gold is published.")
    st.stop()

st.title("✈️ SkyHop Airlines · Operations & Revenue")
st.caption(f"Source: {label} · business day = Europe/London · OTP15 = delay ≤ {OTP_THRESHOLD_MIN} min")

with st.sidebar:
    st.header("Filters")
    dmin, dmax = min(otp_all["business_date"]), max(otp_all["business_date"])
    period = st.date_input("Business days", value=(dmin, dmax), min_value=dmin, max_value=dmax)
    d1, d2 = (period if isinstance(period, (list, tuple)) and len(period) == 2 else (dmin, dmax))
    labels = (otp_all[["origin_airport", "origin_city"]].drop_duplicates()
              .assign(lbl=lambda d: d["origin_airport"] + " · " + d["origin_city"].fillna("?"))
              .sort_values("lbl"))
    picked = st.multiselect("Origin airports", labels["lbl"].tolist(), placeholder="All airports")
    airports = labels.loc[labels["lbl"].isin(picked), "origin_airport"].tolist() if picked else labels["origin_airport"].tolist()
    st.divider()
    st.caption("Limitation: simulated delays are uniform 0–240 min, so the OTP level is not realistic. "
               "Bookings = direct channel only. UK261 = upper bound (no exemptions).")

otp = otp_all[(otp_all["business_date"] >= d1) & (otp_all["business_date"] <= d2) & otp_all["origin_airport"].isin(airports)]
fp = fp_all[(fp_all["business_date"] >= d1) & (fp_all["business_date"] <= d2) & fp_all["origin_airport"].isin(airports)]
if otp.empty:
    st.warning("No flight for these filters.")
    st.stop()

k = kpis(otp, fp)
c = st.columns(6)
c[0].metric("Flights operated", fmt(k["flights"], "int"))
c[1].metric("On-time (OTP15)", fmt(k["otp15"], "pct"))
c[2].metric("Average delay", fmt(k["avg_delay"], "min"))
c[3].metric("Net revenue", fmt(k["net_revenue"], "gbp"), help=f"Refunded: {fmt(k['refunded'], 'gbp')}")
c[4].metric("Direct load factor", fmt(k["load_factor"], "pct"))
c[5].metric("UK261 exposure", fmt(k["uk261"], "gbp"), help=f"{k['delayed_3h']} flights delayed ≥ 3 h · £220 per passenger")

tab_ops, tab_rev = st.tabs(["UC1 · Operations control", "UC2 · Revenue & compensation"])

with tab_ops:
    daily = (otp.groupby("business_date", as_index=False)
             .agg(on_time=("on_time_flights", "sum"), with_delay=("flights_with_delay", "sum"),
                  flights=("flights_operated", "sum"), delayed_3h=("flights_delayed_3h_plus", "sum")))
    daily["otp15_pct"] = 100 * daily["on_time"] / daily["with_delay"].where(daily["with_delay"] > 0)
    left, right = st.columns([3, 2])
    with left:
        st.subheader("On-time performance per day")
        base = alt.Chart(daily).encode(x=alt.X("business_date:T", title=None))
        st.altair_chart(
            alt.layer(base.mark_bar(color=GREY, opacity=0.35).encode(y=alt.Y("flights:Q", title="flights")),
                      base.mark_line(color=NAVY, point=True).encode(y=alt.Y("otp15_pct:Q", title="OTP15 %"),
                                                                     tooltip=["business_date:T", alt.Tooltip("otp15_pct:Q", format=".1f"), "flights:Q"]))
            .resolve_scale(y="independent").properties(height=300), use_container_width=True)
    with right:
        st.subheader("Where to put the standby aircraft")
        by_ap = (otp.groupby(["origin_airport", "origin_city"], as_index=False)
                 .agg(delayed_3h=("flights_delayed_3h_plus", "sum"), flights=("flights_operated", "sum"))
                 .sort_values("delayed_3h", ascending=False).head(10))
        by_ap["airport"] = by_ap["origin_airport"] + " · " + by_ap["origin_city"].fillna("?")
        st.altair_chart(alt.Chart(by_ap).mark_bar(color=RED).encode(
            x=alt.X("delayed_3h:Q", title="flights delayed ≥ 3 h"), y=alt.Y("airport:N", sort="-x", title=None),
            tooltip=["airport", "delayed_3h", "flights"]).properties(height=300), use_container_width=True)
    if "precipitation_mm" in otp.columns and otp["precipitation_mm"].notna().any():
        st.subheader("Delay vs rain at origin (Open-Meteo)")
        st.altair_chart(alt.Chart(otp).mark_circle(color=NAVY, opacity=0.5).encode(
            x=alt.X("precipitation_mm:Q", title="precipitation (mm)"), y=alt.Y("avg_delay_min:Q", title="avg delay (min)"),
            tooltip=["business_date:T", "origin_city", "avg_delay_min", "precipitation_mm"]), use_container_width=True)

with tab_rev:
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Net revenue and UK261 exposure per day")
        rev = (fp.groupby("business_date", as_index=False)
               .agg(net_revenue_gbp=("net_revenue_gbp", "sum"), uk261_exposure_gbp=("uk261_exposure_gbp", "sum")))
        base = alt.Chart(rev).encode(x=alt.X("business_date:T", title=None))
        st.altair_chart(
            alt.layer(base.mark_bar(color=NAVY, opacity=0.85).encode(y=alt.Y("net_revenue_gbp:Q", title="net revenue £ (bars)")),
                      base.mark_line(color=AMBER, point=True, strokeWidth=2.5).encode(
                          y=alt.Y("uk261_exposure_gbp:Q", title="UK261 exposure £ (line)"),
                          tooltip=["business_date:T", alt.Tooltip("net_revenue_gbp:Q", format=",.0f"),
                                   alt.Tooltip("uk261_exposure_gbp:Q", format=",.0f")]))
            .resolve_scale(y="independent").properties(height=300), use_container_width=True)
    with right:
        st.subheader("Weakest flights (direct load factor)")
        weak = (fp[fp["load_factor_pct"].notna()].sort_values(["load_factor_pct", "net_revenue_gbp"]).head(10)
                [["flight_id", "flight_number", "business_date", "origin_airport", "destination_airport",
                  "load_factor_pct", "net_revenue_gbp"]])
        st.dataframe(weak, hide_index=True, use_container_width=True,
                     column_config={"load_factor_pct": st.column_config.NumberColumn("LF %", format="%.2f"),
                                    "net_revenue_gbp": st.column_config.NumberColumn("net £", format="%.2f")})
    st.subheader("Largest compensation exposures (delay ≥ 180 min)")
    top = fp[fp["uk261_exposure_gbp"] > 0].sort_values("uk261_exposure_gbp", ascending=False).head(10)
    st.dataframe(top[["flight_id", "flight_number", "business_date", "origin_airport", "delay_min", "bookings_sold",
                      "uk261_exposure_gbp"]], hide_index=True, use_container_width=True)

st.caption(f"{len(fp_all):,} flights and {len(otp_all):,} day×airport rows in gold · cached 10 min · "
           "no personal data on this page (gold contains none)")
