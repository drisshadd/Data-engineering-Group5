# Platform contract — names everyone uses (please 👍 or correct tonight)

One Snowflake account (Member 1's), one database. Created by `infra/terraform` (+ manual SQL for logins).

| Object | Name | Used by | Notes |
|---|---|---|---|
| Database | `SKYHOP` | all | existed, adopted by Terraform |
| Raw layer | `SKYHOP.BRONZE` | M1 writes, M2 reads | existed; all TEXT + `_SOURCE_FILE`, `_LOADED_AT` |
| Clean layer | `SKYHOP.SILVER` | M2 (dbt) | new |
| Business layer | `SKYHOP.GOLD` | M2 writes, dashboard reads | new; dashboard expects `DAILY_OTP`, `FLIGHT_PERFORMANCE` (`dashboard/GOLD_CONTRACT.md`) |
| Rejected rows | `SKYHOP.QUARANTINE` | M2 (dbt) | new; one row per rejected record + reason |
| Warehouse | `SKYHOP_WH` | ingestion, dashboard | existed; XS, suspends after 60 s |
| Warehouse | `SKYHOP_TRANSFORM_WH` | dbt | new; XS, 60 s |
| Role | `SKYHOP_INGEST` | ingestion job (`SKYHOP_INGEST_SVC`) | existed (M1's SQL) |
| Role | `SKYHOP_TRANSFORM` | dbt (`MEMBER2_DBT`) | new; SELECT bronze, builds silver/gold/quarantine |
| Role | `SKYHOP_ANALYST` | dashboard, panel demo | new; SELECT on GOLD only |
| Credit limit | `SKYHOP_MONITOR` | both warehouses | 20 credits / month, suspend at 100 % |

## For Member 2 (dbt `profiles.yml`)
```yaml
skyhop:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: <org>-<account>
      user: MEMBER2_DBT
      role: SKYHOP_TRANSFORM
      warehouse: SKYHOP_TRANSFORM_WH
      database: SKYHOP
      schema: SILVER
      threads: 4
```
dbt by default names custom schemas `SILVER_GOLD`. Add a `generate_schema_name` macro that returns the custom
schema name as-is, so models land in `SKYHOP.GOLD` / `SKYHOP.QUARANTINE` (the role can't create new schemas).

## For the DAG (Member 3, Phase 2)
`ingest files → ingest postgres → ingest apis → ingest verify → dbt build (run + test) → alert on failure`.
Commands and env vars: `docs/member1/HANDOVER_TO_M2.md` §5.
