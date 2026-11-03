# SkyHop — Member 2 to Member 3 integration handoff (updated 3 November 2026)

## Current state: dbt is integrated and tested

The Member 2 dbt project is merged into the team's `main` branch under `dbt/`. On the shared Snowflake account, the team has executed **dbt build successfully**: 14 tables + 2 views + 37 data tests = **53 PASS, 0 WARN, 0 ERROR, 0 SKIP**, in 16.24 seconds. The generated dbt lineage graph was also captured. See [`../docs/evidence/member2/`](../docs/evidence/member2/) for the build, graph, Gold table listing and reconciliation screenshots.

- Snowflake account identifier: `DQYYEIS-EW25504`; database: `SKYHOP`.
- Member 2's initial manual validation used `SKYHOP_ENGINEER` / `SKYHOP_WH`. The integrated dbt configuration targets `SKYHOP_TRANSFORM` / `SKYHOP_TRANSFORM_WH`. Do not conflate the roles.
- All four core Silver tables and two staging views are in `SKYHOP.SILVER`.
- Quarantined records are in `SKYHOP.QUARANTINE.FLIGHTS` (79) and `SKYHOP.QUARANTINE.BOOKINGS` (977).
- Nine Gold tables are present, including `FLIGHT_PERFORMANCE`, `DAILY_OTP`, `ROUTE_PERFORMANCE`, `AIRPORT_PEAK_HOURS`, `LOYALTY_REVENUE`, `WEATHER_IMPACT`, `ROUTE_WEATHER_READINESS`, `PASSENGER_DISRUPTIONS` and the legacy `PASSENGER_DISRUPTION` table. The singular table was created manually; the plural table is the dbt model.
- The dashboard uses **only** `SKYHOP.GOLD.DAILY_OTP` and `SKYHOP.GOLD.FLIGHT_PERFORMANCE`, as specified in [`../dashboard/GOLD_CONTRACT.md`](../dashboard/GOLD_CONTRACT.md).

## Dashboard data contract

- `GOLD.FLIGHT_PERFORMANCE`: one row per valid flight. Dashboard fields include `FLIGHT_ID`, `FLIGHT_NUMBER`, `BUSINESS_DATE`, `ORIGIN_AIRPORT`, `DESTINATION_AIRPORT`, `SEATS`, `DELAY_MIN`, `BOOKINGS_SOLD`, `BOOKINGS_REFUNDED`, `NET_REVENUE_GBP`, `REFUNDED_GBP`, `LOAD_FACTOR_PCT`, and `UK261_EXPOSURE_GBP`. Additional aliases `BOOKING_COUNT`, `REVENUE_GBP`, `IS_ON_TIME`, and `SCHEDULED_DEPARTURE_UTC` support other Gold models.
- `GOLD.DAILY_OTP`: one row per **London business date × origin airport** (436 baseline rows), with `BUSINESS_DATE`, `ORIGIN_AIRPORT`, `ORIGIN_CITY`, `FLIGHTS_OPERATED`, `FLIGHTS_WITH_DELAY`, `ON_TIME_FLIGHTS`, `OTP15_PCT`, `AVG_DELAY_MIN`, `FLIGHTS_DELAYED_3H_PLUS` plus additional reconciliation columns.
- Refunds are identified by `SILVER_BOOKINGS.IS_REFUND`. Silver keeps positive fare magnitudes; Gold's net revenue **excludes refunded bookings**.

## Two-batch baseline confirmed after dbt build

| Metric | Value |
|---|---:|
| Silver flights | 866 |
| Silver bookings | 8,123 |
| Sold bookings | 8,034 |
| Refunds | 89 |
| Quarantined flights | 79 |
| Quarantined bookings | 977 |
| Net revenue GBP | 1,788,710.02 |
| Daily OTP date×airport rows | 436 |
| Flights with known delay | 853 |
| On-time flights (≤15 minutes) | 61 |
| Estimated UK261 exposure GBP | 419,540 |

Use [`reconciliation.sql`](reconciliation.sql) for the complete baseline SQL. `FLIGHTS_WITH_DELAY = 853` means a non-null delay value, **not** 853 late flights.

## What Member 3 can reuse for orchestration

The successful dbt command operates on the checked-in `dbt/` directory with its model dependencies and tests. Credentials must be supplied securely outside Git; use [`profiles.yml.example`](profiles.yml.example) as the template. The dbt role is `SKYHOP_TRANSFORM`, the warehouse is `SKYHOP_TRANSFORM_WH`, and the database is `SKYHOP`.

The agreed Airflow task order is:

1. `python -m skyhop_ingest files --batch <available_batch>`
2. `python -m skyhop_ingest postgres` (watermark based; **no** `--batch` argument)
3. `python -m skyhop_ingest apis --start 2026-06-01 --end 2026-09-30`
4. `python -m skyhop_ingest verify` (must succeed before dbt)
5. `dbt build` from `dbt/` using the authorized Snowflake profile

Refer to [`../docs/member1/HANDOVER_TO_M2.md`](../docs/member1/HANDOVER_TO_M2.md) §5 for ingestion variables, mounts, images and commands. Do not put passwords, key files, `.env` values or `profiles.yml` with credentials in GitHub. Use the appropriate ingestion role for Bronze and transform role for dbt. Test each task's failure/retry behavior and capture evidence of a fully green DAG run and a failed/alerted run. The dbt build screenshot alone is **not** Airflow evidence.

## Permissions and governance

- `SKYHOP_ANALYST` has `USAGE` on SKYHOP/GOLD/SKYHOP_WH and `SELECT` on Gold tables. An interactive Snowflake test confirmed it could read Gold but not restricted `SILVER.SILVER_PASSENGERS`.
- The Gold reporting models do not expose passenger `FULL_NAME` or `EMAIL`. Do not claim masking policies were deployed unless independently verified.
- Terraform has imported the already-existing SILVER/GOLD/QUARANTINE schemas; the Terraform commit reported no destructive changes. Retain infrastructure ownership and grants during any further redeployment.

## Quality and presentation caveats

- Member 2 captured 6/6 passing manual integrity checks, 977 booking quarantine reasons and 79 flight quarantine reasons; the dbt build screenshot separately reports 37 passing dbt tests.
- Quarantine scenarios are examples of **rejected data**, not proof of an Airflow incident/recovery. Airflow retries and alerts must be demonstrated separately.
- Weather correlations describe associations, not proof that weather caused delays. UK261 is an estimated exposure, not actual compensation paid. Route revenue is not route profit.
- These figures apply to the two-batch seed-42 reference dataset; new batches may change the numbers. Do not hard-code these totals as universal production SLAs.
