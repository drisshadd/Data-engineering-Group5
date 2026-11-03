# SkyHop Member 2 — Integration, validation and defense

## Current status
- Prepared: dbt models, tests, sources, macros and example profile.
- Offline verified: YAML parses, Jinja parses, all `ref()` model dependencies resolve.
- Not verified: dbt compile/build against real Snowflake; live reconciliation; role privileges; 5 fully demonstrated business use cases.
- Critical caveat: `route_weather_readiness` reports weather source availability only. It is **not** weather correlation.
- `route_performance` reports revenue and load factor, not profit without costs.

## Team handoff
- Member 1: ensure BRONZE tables exist and share raw column definitions and source update status.
- Member 3: grant SKYHOP_TRANSFORM access to BRONZE and CREATE on SILVER/GOLD/QUARANTINE; confirm warehouse and role; orchestrate `dbt build`.
- Member 2: deploy this `dbt/` directory; run and resolve compilation, test and reconciliation failures; produce lineage docs.

## Safe integration order
1. Add `dbt/` to a feature branch, not directly to `main` if possible. Do not commit secrets.
2. Create a local Python environment and `pip install dbt-snowflake`.
3. Copy `profiles.yml.example` to `~/.dbt/profiles.yml` and set environment variables locally (never paste credentials into chat).
4. From `dbt/`, run `dbt debug`, `dbt parse`, `dbt compile`.
5. Run `dbt build --select silver_airports silver_passengers silver_flights silver_bookings` first; fix errors before proceeding.
6. Run `dbt build` for all models and tests; inspect failing tests.
7. Execute `reconciliation.sql` in Snowsight and compare against `dashboard/sample_data/expected_totals.json`, verifying the same source batch count.
8. Run `dbt docs generate` and capture lineage screenshot; share the generated artifact and command output with Member 3.

## Demo sequence
1. Show BRONZE raw anomalies and SILVER normalized values.
2. Show QUARANTINE rows with `quarantine_reason`.
3. Show GOLD `FLIGHT_PERFORMANCE` and `DAILY_OTP` feeding the dashboard.
4. Demonstrate duplicate batch replay with stable counts, and malformed/schema-drift records with quarantine or recovery.
5. Show dbt test results and lineage; explain UTC timestamps versus London reporting dates.

## Security
- Treat passenger names/emails as personal data. Keep access to SILVER_PASSENGERS restricted.
- Never commit a real profiles.yml, private key, token or password.
- Rotate any credentials posted into chat or a shared group message.
