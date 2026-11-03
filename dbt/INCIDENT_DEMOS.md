# SkyHop Member 2 — reproducible incident demonstrations

Do **not** edit production Bronze data for a presentation. Run read-only queries and use a development schema or local fixture for fault injection. The scripts below demonstrate checks and recovery criteria; they are **not** proof that incidents have been executed in Snowflake.

## Incident 1 — Duplicate replay / revenue inflation

**Failure:** a Bronze batch is replayed; a naïve SUM across raw bookings doubles revenue.

**Detection:** compare Bronze counts with deduplicated Silver, and test Gold flight grain:

```sql
select count(*) as raw_bookings, count(distinct try_to_number(booking_id)) as distinct_booking_ids
from SKYHOP.BRONZE.BOOKINGS;
select count(*) as clean_bookings, count(distinct booking_id) as distinct_clean_ids
from SKYHOP.SILVER.SILVER_BOOKINGS;
select flight_id, count(*) as n from SKYHOP.GOLD.FLIGHT_PERFORMANCE group by 1 having count(*) > 1;
```

**Recovery:** re-run `dbt build`; staging ranks records by batch and selects one version per business key. Confirm that Gold revenue and flight counts are unchanged after replay. Do not claim this is a Snowflake MERGE: the delivered dbt Silver models are full-refresh tables and use deterministic ranking, not incremental MERGE.

## Incident 2 — Bookings schema drift

**Failure:** batch 2 uses `booked_at_v2` instead of `booked_at`.

**Detection:** inspect both raw fields and verify the normalized Silver timestamp:

```sql
select count_if(booked_at is not null) as legacy_timestamp_rows,
       count_if(booked_at_v2 is not null) as renamed_timestamp_rows
from SKYHOP.BRONZE.BOOKINGS;
select count(*) as clean_bookings,
       count_if(booked_at_utc is null) as missing_or_invalid_timestamps
from SKYHOP.SILVER.SILVER_BOOKINGS;
```

**Recovery:** the staging model uses `coalesce(booked_at, booked_at_v2)` before timestamp parsing. Run `dbt build` and inspect the `bookings_quarantine` table. Both columns must physically exist in the Bronze schema for the current SQL to compile.

## Incident 3 — Weather source unavailable (optional)

**Failure:** Open-Meteo API fails or returns no matching dates.

**Detection:** `dbt test --select assert_weather_coverage` produces a warning. Inspect `weather_available` in `GOLD.WEATHER_IMPACT`.

**Recovery:** ingestion retries the API separately; the Gold left join preserves flight KPIs and marks missing weather, rather than inventing zero precipitation.

## Presentation evidence to capture

- Screenshot of failing test or warning in a **development** run
- SQL showing rejected rows or missing coverage
- Recovery run log with tests passing
- Counts and Gold metrics before and after rerun
- dbt lineage showing BRONZE → SILVER → GOLD
