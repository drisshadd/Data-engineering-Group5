# SkyHop — Member 2 use cases and handoff

| Use case | Gold model | Decision supported | Caveat |
|---|---|---|---|
| UC1 Punctuality | `daily_otp` | Which origins have the worst daily on-time performance? | Business day currently Europe/London |
| UC2 Route capacity/revenue | `route_performance`, `flight_performance` | Where should schedules/capacity be reviewed? | Revenue ≠ profit; no cost model |
| UC3 Weather disruption | `weather_impact` | Which airport-days with high rain/wind also have more delays? | City-level daily association, not causality |
| UC4 Passenger disruption | `passenger_disruptions` | Where are bookings exposed to 3h+ delays? | Bookings proxy for passengers; UK261 is illustrative exposure |
| UC5 Airport peak windows | `airport_peak_hours` | When are scheduled departures busiest? | Scheduled volume ≠ ATC congestion |
| Bonus UC6 Loyalty value | `loyalty_revenue` | Which tiers account for sales? | Gross sales, not lifetime value |

## Critical handoff to Member 1

`SKYHOP.GOLD.DAILY_OTP` and `SKYHOP.GOLD.FLIGHT_PERFORMANCE` are the dashboard-facing models. Confirm the exact expected columns in dashboard code before changing their names.

## Critical handoff to Member 3

Run `dbt deps`, `dbt debug`, `dbt compile`, then `dbt build` with the Snowflake `SKYHOP_TRANSFORM` role. Ensure the custom schema naming macro is active so models land in `SKYHOP.SILVER`, `SKYHOP.GOLD`, and `SKYHOP.QUARANTINE` rather than schema-prefixed variants. Run from the dbt project directory; never commit credentials.

## Governance

- `SILVER_PASSENGERS` includes names and email; restrict its access.
- GOLD models expose aggregate loyalty and booking metrics without direct passenger identifiers.
- Do not claim row-level masking policies are implemented until verified in Snowflake.
- Store event timestamps in UTC, with the agreed `Europe/London` business date for this current implementation. The more precise departure-airport-local business date is a future improvement.
