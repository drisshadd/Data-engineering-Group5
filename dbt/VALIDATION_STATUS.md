# Member 2 validation status — 2026-11-03

## Completed
- Manual Snowflake SQL: 4 Silver tables, 2 staging views, 2 quarantine tables, 5 Gold tables.
- Reconciliation: 866 valid flights; 8,123 valid bookings; 79 quarantined flights; 977 quarantined bookings; £1,788,710.02 revenue excluding refunds.
- Six manual SQL quality checks returned zero failures.
- Two quarantine reason breakdowns captured by user.
- Offline Jinja template rendering: 16 dbt models + 14 custom SQL tests; all `ref()` targets resolve; YAML parsed; key dashboard output columns checked.

## Not completed / do not claim
- Actual `dbt debug`, `dbt compile`, `dbt build`, `dbt test` against Snowflake.
- `dbt docs generate` / published lineage graph.
- Airflow end-to-end run, alerting, retries, incident recovery.
- Role-based PII grants/masking policy verified in live Snowflake.
- Live validation of optional dbt weather/loyalty models and schema-level dashboard compatibility after dbt rebuild.

## Warnings
- Static Jinja rendering is not equivalent to dbt compilation or Snowflake SQL execution.
- A dbt build can replace existing manually created tables and change dashboard dependencies. Coordinate deployment with Member 3.
- The manually created `PASSENGER_DISRUPTION` (singular) differs from the packaged dbt model `PASSENGER_DISRUPTIONS` (plural).
- The baseline counts reflect the currently loaded Bronze batches and will change with new ingestion.
