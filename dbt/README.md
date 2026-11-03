# SkyHop Member 2 — dbt transformation package

## Install / run
1. Copy this folder to the team's repository as `dbt/` (do not replace Member 1 or Member 3 files).
2. Install `dbt-snowflake` in a Python virtual environment.
3. Copy `profiles.yml.example` to `~/.dbt/profiles.yml` (never commit real credentials).
4. Export `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD` securely.
5. Confirm Member 3 has created SILVER, GOLD, QUARANTINE and granted SKYHOP_TRANSFORM privileges.
6. `cd dbt && dbt debug && dbt deps && dbt compile && dbt build`
7. `dbt docs generate && dbt docs serve`; execute `reconciliation.sql` in Snowsight.

## Data flow
BRONZE → SILVER_AIRPORTS / SILVER_PASSENGERS → STG_FLIGHTS_RANKED → SILVER_FLIGHTS → STG_BOOKINGS_RANKED → SILVER_BOOKINGS → GOLD.
Quarantine tables use ranked staging models, preserving reasons and metadata.

## Known limitations / required live verification
- No Snowflake credentials in the ZIP. SQL is not executed against the actual account here.
- The reference uses Python datetime parsing. The Snowflake macro supports ISO, offsets, epoch, and day-first text, but actual SQL conversion needs comparison against sample records.
- Snowflake's `TRY_TO_TIMESTAMP_TZ` can interpret some numeric strings differently; epoch branch should be validated on raw sample values.
- Duplicate tie-breaking includes `_source_file` and `_loaded_at`; exact row-level parity with Python may differ for identical tied values.
- Source freshness test checks presence, not a strict SLA; source timestamps in historical demonstrations can be old.
- Passengers' names/emails remain in restricted SILVER only. Confirm Member 3 role grants prevent analyst access to SILVER.
- The weather model is a readiness check only, not a correlation claim. Do not present it as a completed weather-impact use case.
- Route revenue is not route profit without costs; UK261 is an estimate only.
- Current Gold outputs cover OTP, routes, passenger disruption, peak-hour patterns, loyalty. Weather correlation awaits API payload inspection.
- Expected numbers depend on exact batch count; 3 batches cannot be reconciled to 2-batch reference totals.

## 2026-11-03 integration correction
Read `MEMBER3_HANDOFF.md` and `VALIDATION_STATUS.md` before running dbt. The package preserves the existing manually validated Gold dashboard columns and refund revenue definition. Live dbt execution remains pending; the package is **not** a successful dbt run report.
