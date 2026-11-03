# Member 2 — Validation status (updated 3 November 2026)

## Verified in Snowflake and dbt

- The team's `dbt build` completed successfully: **PASS=53, WARN=0, ERROR=0, SKIP=0** in 16.24 seconds (14 table models, 2 view models, 37 data tests). Screenshot: [`../docs/evidence/member2/dbt_build_53_pass.png`](../docs/evidence/member2/dbt_build_53_pass.png).
- Generated dbt lineage documentation shows Bronze sources, staging and Silver models, quarantine branches, Gold models and tests. Screenshot: [`../docs/evidence/member2/dbt_lineage_graph.png`](../docs/evidence/member2/dbt_lineage_graph.png).
- In Snowflake, the four core Silver tables and both quarantine tables were validated. Nine Gold tables appear in the post-build object listing. Evidence: [`../docs/evidence/member2/`](../docs/evidence/member2/).
- Six read-only data-integrity checks returned zero failures: missing/duplicate flight and booking IDs, booking-to-flight referential integrity, and negative Gold flight revenue.
- The team reconciled the **two-batch, seed-42 baseline** to all eleven targets below. The reconciliation query is [`reconciliation.sql`](reconciliation.sql).

| Metric | Verified value |
|---|---:|
| Accepted Silver flights | 866 |
| Accepted Silver bookings | 8,123 |
| Sold bookings (excluding refunds) | 8,034 |
| Refunded bookings | 89 |
| Quarantined flights | 79 |
| Quarantined bookings | 977 |
| Net revenue (GBP, excluding refunds) | 1,788,710.02 |
| Daily OTP rows (London business date × origin airport) | 436 |
| Flights with known delay | 853 |
| On-time flights (delay ≤ 15 min) | 61 |
| Estimated UK261 exposure (GBP) | 419,540 |

**Terminology:** 853 is the count of flights **with a known delay**, not the count of delayed flights. UK261 exposure is a scenario estimate, not paid compensation. Route revenue is not route profit. Bookings are a proxy for passengers where indicated.

## Governance verified

- `SHOW GRANTS TO ROLE SKYHOP_ANALYST` showed database/Gold/warehouse usage and `SELECT` on nine Gold tables, with no direct grants to Bronze, Silver or Quarantine.
- An interactive test using `SKYHOP_ANALYST` could read `SKYHOP.GOLD.FLIGHT_PERFORMANCE` (866 rows) but could **not** read `SKYHOP.SILVER.SILVER_PASSENGERS` (authorization error). The result was confirmed by Member 2; the separate access-test screenshot has not been committed to this evidence folder.
- `FULL_NAME` and `EMAIL` stay within the restricted Silver passenger model, not the dashboard-facing Gold models. **Do not claim a Snowflake masking policy has been implemented** unless a policy and its execution are separately evidenced.

## Incident demonstrations

- Booking quarantine contains 977 rejected records with explicit reasons (including unknown/quarantined flights, malformed fares and EUR values in a GBP feed).
- Flight quarantine contains 79 rejected records with explicit reasons (including identical endpoints, unknown airports and unreadable departure times).
- These are **data-quality incidents**, not proof of an Airflow outage, automatic recovery or alert delivery. See [`INCIDENT_DEMOS.md`](INCIDENT_DEMOS.md).

## Remaining team-level verification

- Scheduled Airflow DAG run, retry/alert evidence and end-to-end automation are a separate Member 3 integration task; they are **not established by the dbt build screenshot**.
- Present the Gold/lineage/dbt evidence as captured on 3 November 2026. Subsequent new Bronze batches can change the baseline metrics.
- The repository contains both the legacy manual `GOLD.PASSENGER_DISRUPTION` (singular) and dbt `GOLD.PASSENGER_DISRUPTIONS` (plural). The current dashboard reads `DAILY_OTP` and `FLIGHT_PERFORMANCE` only.
