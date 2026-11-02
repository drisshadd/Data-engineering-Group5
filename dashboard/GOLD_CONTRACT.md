# Gold contract — what the dashboard reads (agree with Member 2)

The dashboard reads only `SKYHOP.GOLD.DAILY_OTP` and `SKYHOP.GOLD.FLIGHT_PERFORMANCE` (schema overridable with
`SKYHOP_GOLD_SCHEMA`). Column names are case-insensitive. If dbt names the models differently, either create two
views with these names or change the two `SELECT` in `dashboard/app.py`.

## DAILY_OTP — 1 row per London business day × origin airport
| Column | Type | Meaning |
|---|---|---|
| business_date | DATE | UTC departure converted to Europe/London |
| origin_airport | VARCHAR | e.g. AP009 |
| origin_city | VARCHAR | e.g. London |
| flights_operated | NUMBER | valid flights (not quarantined) |
| flights_with_delay | NUMBER | flights with a known delay (OTP denominator) |
| on_time_flights | NUMBER | delay ≤ 15 min |
| otp15_pct | NUMBER | 100 × on_time / with_delay (dashboard recomputes from counts) |
| avg_delay_min | NUMBER | average known delay |
| flights_delayed_3h_plus | NUMBER | delay ≥ 180 min |
| precipitation_mm, wind_max_kmh | FLOAT | *optional* (Open-Meteo): extra chart appears if present |

## FLIGHT_PERFORMANCE — 1 row per flight_id
| Column | Type | Meaning |
|---|---|---|
| flight_id, flight_number | NUMBER, VARCHAR | |
| business_date, origin_airport, destination_airport | DATE, VARCHAR, VARCHAR | |
| seats, delay_min | NUMBER | NULL when out of range |
| bookings_sold, bookings_refunded | NUMBER | refunds excluded from revenue and load factor |
| net_revenue_gbp, refunded_gbp | NUMBER(14,2) | |
| load_factor_pct | NUMBER | 100 × sold / seats (direct channel) |
| uk261_exposure_gbp | NUMBER | 220 × sold if delay ≥ 180 |

## Acceptance (tested: `tests/member1/test_dashboard.py`)
On the expected gold (seed 42, 2 batches) the tiles show: 866 flights · OTP15 7.2 % (61/853) ·
net revenue £1,788,710 · UK261 £419,540. When Member 2's gold is published, the same numbers must appear
with `SKYHOP_DASH_SOURCE=snowflake`.
