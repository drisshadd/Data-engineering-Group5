# Member 2 — dbt, Silver/Gold, data quality and governance evidence

Captured 3 November 2026 from the SkyHop team Snowflake/dbt project. These files document observed results; do not confuse this evidence with an Airflow DAG run.

## Evidence files

- `dbt_build_53_pass.png` — dbt `build` reported **PASS=53, WARN=0, ERROR=0, SKIP=0**: 14 table models, 2 view models, 37 data tests, 16.24 seconds.
- `dbt_lineage_graph.png` — generated dbt lineage showing Bronze sources → Silver/staging → quarantine and Gold models with attached tests.
- `gold_reconciliation_member3.png` — Snowflake result: 866 flights, 61 on-time flights, 853 flights with known delay values, GBP 1,788,710.02 net revenue, GBP 419,540 indicative UK261 exposure.
- `gold_nine_tables.png` — nine Gold table names shown in Snowsight after dbt build.

## Verified by Member 2 in Snowflake (interactive access tests)

- Six manual data-integrity checks returned zero failures (missing or duplicated IDs, orphan booking flight IDs, and negative Gold revenue).
- `SHOW GRANTS TO ROLE SKYHOP_ANALYST` showed USAGE on SKYHOP/GOLD/SKYHOP_WH, SELECT on nine Gold tables, and no direct Bronze, Silver or Quarantine privileges.
- Switching to `SKYHOP_ANALYST`, reading `SKYHOP.GOLD.FLIGHT_PERFORMANCE` succeeded with 866 rows; attempting to read `SKYHOP.SILVER.SILVER_PASSENGERS` failed authorization as expected. This access test was reported in chat, but a separate screenshot of it is **not included here**.
- Quarantine breakdowns: 977 bookings (893 unknown flight only, 53 unreadable fare only, 22 EUR-only, 6 unknown flight+unreadable, 3 unknown flight+EUR); 79 flights (48 same endpoints only, 14 unknown destination only, 9 unreadable departure only, 7 unknown origin only, 1 same endpoints+unreadable departure).
- Latest validation: 866 Silver flights; 8,123 Silver bookings; 8,034 sold bookings; 89 refunds; 79 quarantined flights; 977 quarantined bookings; 436 date×airport daily OTP rows; 853 flights with known delay; 61 on-time flights; £1,788,710.02 net revenue; £419,540 estimated UK261 exposure.

## Scope and caveats

The build screenshot establishes successful dbt models/tests at the time captured, and the lineage screenshot proves generated docs were available. This does not prove daily scheduled automation, an Airflow success/alert, or a completed incident recovery rehearsal. Data-quality incident examples describe rejected records, not an infrastructure outage. The Gold UK261 value is a scenario estimate, not actual compensation paid. See `dbt/INCIDENT_DEMOS.md`, `dbt/governance_checks.sql`, `dbt/reconciliation.sql` and `dashboard/GOLD_CONTRACT.md` for implementation details.
