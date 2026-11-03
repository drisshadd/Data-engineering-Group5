# SkyHop Member 2 → Member 3: Integration handoff (2026-11-03)

## Verified live in Snowflake (manual SQL execution, NOT dbt execution)
Account `DQYYEIS-EW25504`, database `SKYHOP`, warehouse `SKYHOP_WH`, role used `SKYHOP_ENGINEER`.
- `SILVER.SILVER_AIRPORTS`, `SILVER.SILVER_PASSENGERS`, `SILVER.SILVER_FLIGHTS`, `SILVER.SILVER_BOOKINGS` exist.
- `SILVER.STG_FLIGHTS_RANKED` and `SILVER.STG_BOOKINGS_RANKED` are manually created views.
- `QUARANTINE.FLIGHTS` 79 rows, `QUARANTINE.BOOKINGS` 977 rows.
- `GOLD.FLIGHT_PERFORMANCE` 866 rows, `GOLD.DAILY_OTP` 31 rows, `GOLD.ROUTE_PERFORMANCE` 295 rows, `GOLD.PASSENGER_DISRUPTION` 31 rows, `GOLD.AIRPORT_PEAK_HOURS` 838 rows.
- 8,123 accepted bookings; net revenue excluding 89 refunds = **£1,788,710.02**; six manually executed integrity checks returned zero failures.
- NOTE: `PASSENGER_DISRUPTION` is the current manual table name; dbt model `passenger_disruptions` would create `PASSENGER_DISRUPTIONS`. Do not swap without coordinating dashboard references.

## Fixes in this handoff package
- `FLIGHT_PERFORMANCE` dbt model preserves dashboard columns `BOOKING_COUNT`, `REVENUE_GBP`, `IS_ON_TIME`, `SCHEDULED_DEPARTURE_UTC`, plus dbt columns `BOOKINGS_SOLD`, `NET_REVENUE_GBP`, `REFUNDED_GBP`, `LOAD_FACTOR_PCT`, `UK261_EXPOSURE_GBP`.
- `DAILY_OTP` dbt model matches existing daily-grain contract (`TOTAL_FLIGHTS`, `ON_TIME_FLIGHTS`, `OTP_PCT`, `AVG_DELAY_MIN`, `TOTAL_BOOKINGS`, `TOTAL_REVENUE_GBP`).
- Refunds remain positive in `SILVER_BOOKINGS.FARE_GBP`, identified by `IS_REFUND`; net revenue excludes them. Reference reconciliation £1,788,710.02.
- `ROUTE_PERFORMANCE`, `AIRPORT_PEAK_HOURS`, `PASSENGER_DISRUPTIONS` updated to retain validated reporting logic. Quarantine models renamed to produce `QUARANTINE.BOOKINGS` and `QUARANTINE.FLIGHTS`.
- Added tests for dashboard column contract, booking count, daily revenue, and baseline quarantine counts (last two warn-only on changed batches).

## Member 3 integration sequence (coordinate before rebuild)
1. Add folder `dbt/` from ZIP to team repository on a branch; merge after review. Do not commit `profiles.yml`, credentials or logs. `.gitignore` excludes them.
2. Confirm Airflow/dbt service role: `USAGE` on database/warehouse, `SELECT` on `BRONZE` tables, and `USAGE`/`CREATE TABLE`/`CREATE VIEW` on `SILVER`, `GOLD`, `QUARANTINE`. Ownership/replace permissions on existing tables may be needed; do not silently change roles or drop existing objects.
3. In an authorized dbt environment, provide `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD` securely; configure `profiles.yml` from `profiles.yml.example` (never put password in Git). Test `dbt debug`, then `dbt parse`, `dbt compile`.
4. **Do not run `dbt build` against production until models are compared with the manually validated baseline**. Prefer separate integration schema/database or controlled maintenance window; custom schema macro currently maps directly to SILVER/GOLD/QUARANTINE, so isolation requires a separate account/database or adjusted macro.
5. Execute `dbt build` and `dbt test`; check baseline reconciliations and dashboard after the run. `dbt docs generate` for lineage. Share command logs, lineage screenshot, and Airflow DAG run evidence.
6. For an Airflow DAG, run Bronze ingestion → dbt build → validation → dashboard refresh, with failure alerting and retries. Confirm permissions using the actual service role.

## Baseline SQL to compare after dbt build
```sql
select count(*) from SKYHOP.SILVER.SILVER_FLIGHTS; -- 866
select count(*) from SKYHOP.SILVER.SILVER_BOOKINGS; -- 8123
select count(*) from SKYHOP.QUARANTINE.FLIGHTS; -- 79
select count(*) from SKYHOP.QUARANTINE.BOOKINGS; -- 977
select round(sum(net_revenue_gbp),2) from SKYHOP.GOLD.FLIGHT_PERFORMANCE; -- 1788710.02
```

## Governance and incident evidence
- PII (`FULL_NAME`, `EMAIL`) resides in `SILVER.SILVER_PASSENGERS`, not the Gold reporting models; verify role-based SELECT grants and masking policies separately.
- Booking incident: 977 rejected records (893 unknown flight only, 53 unreadable fare only, 22 EUR-only, 6 combined unknown+unreadable, 3 combined unknown+EUR).
- Flight incident: 79 rejected records (48 same origin/destination, 14 unknown destination, 9 unreadable departure, 7 unknown origin, 1 combined).
- These are **quarantine data-quality scenarios**, not demonstrated Airflow outage/recovery incidents.
- Weather correlation, loyalty and other optional dbt Gold models exist in code but are not verified live.
