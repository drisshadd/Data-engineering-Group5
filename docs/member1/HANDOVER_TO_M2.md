# Handover Member 1 → Member 2 · Bronze is finished

**Status on handover day** — fill in after the run on Snowflake, then send this file to M2:

| Check | Expected | Done on Snowflake |
|---|---|---|
| `python -m skyhop_ingest verify` | 8 files, all OK, 13,749 rows | [ ] date: ____ |
| `API_RAW` documents | open_meteo 12 · ourairports 12 · frankfurter 1 · govuk 1 · nager 1 | [ ] |
| Replay of batch 1 | PUT SKIPPED, COPY 0 file, counts unchanged | [ ] |
| Screenshots in `docs/evidence/member1/` | LIST @LANDING · counts query · COPY_HISTORY · API_RAW | [ ] |

## 1. What you get (database `SKYHOP`, schema `BRONZE`)
Every column is `VARCHAR` (raw text exactly as in the source), plus `_SOURCE_FILE` (e.g.
`reservations/batch_002/bookings.csv.gz`) and `_LOADED_AT`. Nothing is rejected in bronze.

| Table | Source | Rows (seed 42) | Natural key | Notes |
|---|---|---|---|---|
| AIRPORTS | flight-ops files | 20 (18 + 2) | airport_code | batch 2 re-sends 2 airports (late update) |
| FLIGHTS | flight-ops files | 976 (928 + 48) | flight_id | 945 distinct ids → duplicates + updates |
| PASSENGERS | reservation DB (PostgreSQL) | 3,257 (3,096 + 161) | passenger_id | **PII**: full_name, email → mask in silver/gold |
| BOOKINGS | reservation DB (PostgreSQL) | 9,496 (7,224 + 2,272) | booking_id | 9,100 distinct ids; **schema drift** in batch 2 |
| API_RAW | 5 public APIs | 27 documents | (source, request_key) | `payload` VARIANT, see §3 |
| CITY_REFERENCE | seed | 12 | city | city → IATA, coordinates, holiday calendar |

Batch number of a row: `TRY_TO_NUMBER(REGEXP_SUBSTR(_source_file, 'batch_([0-9]+)', 1, 1, 'e', 1))`.
**Latest batch wins** for the same id (batch 2 contains corrections of batch 1).

## 2. What must be cleaned (full detail: `bronze_profile.md`, ground truth: `issues_report.json`)
| Column | What I found in bronze | Suggested rule |
|---|---|---|
| all | `''`, `' '`, `N/A`, `null`, `NULL`, `-` used as missing | → NULL |
| bookings.fare_gbp | `£393.31`, `380.07 GBP`, `237,06`, `' 59.43 '`, negative (refunds), `€60.79` (30 raw rows), ×100 outliers (pence) | parse; negative = refund; ≥ 1000 → ÷100; € → quarantine (never convert) |
| *.booked_at / scheduled_departure | `+01:00` offsets, `yyyy-mm-dd hh:mi:ss`, epoch seconds, `dd/mm/yyyy hh:mi`, 1970 / 2099 defaults | → UTC; 1970/2099 → NULL; business day = Europe/London |
| bookings.booked_at_v2, source_system | only in batch 2 (column renamed by the source) | `COALESCE(booked_at, booked_at_v2)` |
| flights.delay_min, seats | `' 5 '`, `138 units`, negative, ×1000 | parse digits; range delay 0–1440, seats 50–400 else NULL |
| flights.origin / destination | `AP003X` (orphans), missing, origin = destination | quarantine the flight (and its bookings) |
| flights.flight_number | `sh874` lower case, blanks | UPPER, NULL |
| cabin / frequent_flyer_tier | `BUSINESS`, `businesss`, `' premium '`, `platinums` | lower + trim + prefix match |
| passengers.email | upper case, leading spaces, missing `@`, `test@test.com` | lower/trim; invalid → NULL |
| passengers.full_name | `Ã©` broken encoding, `LAST, First` | keep raw (PII, not used in gold) |
| ids | exact duplicates, near duplicates, updates | one row per id, latest batch, deterministic tie-break |

## 3. API_RAW — where the data is inside `payload`
| source | entity | request_key | Path in payload |
|---|---|---|---|
| open_meteo | city (London…) | `city|start|end` | `payload:daily:time[i]`, `precipitation_sum[i]`, `wind_speed_10m_max[i]`, `temperature_2m_max[i]` (daily, Europe/London) |
| frankfurter | EURGBP | `EURGBP|start|end` | `payload:rates:"2026-09-01":GBP` = GBP per 1 EUR (business days only → use last rate ≤ date) |
| govuk_bank_holidays | GB | bank-holidays | `payload:"england-and-wales":events[i]:date / title` (also scotland, northern-ireland) |
| nager_date | FR | `FR|2026` | `payload[i]:date`, `payload[i]:name` |
| ourairports | IATA | IATA | `payload:name`, `latitude_deg`, `longitude_deg` |

Window loaded: 1 June → 30 Sept 2026 (bookings start 1 June, last flight 30 Sept).

## 4. What I expect back (for my dashboard)
Gold tables as in `dashboard/GOLD_CONTRACT.md`. Acceptance: the dashboard on Snowflake shows the same
numbers as on the offline sample (866 flights · OTP15 7.2 % · £1,788,710 · UK261 £419,540).

## 5. For Member 3 (DAG): one command = one task
```
skyhop-ingest:1.0.0 files              --batch {{ params.batch }}      # source 1
skyhop-ingest:1.0.0 postgres                                           # source 2 (watermark, no batch needed)
skyhop-ingest:1.0.0 apis               --start 2026-06-01 --end 2026-09-30
skyhop-ingest:1.0.0 verify                                             # bronze gate before dbt
```
Env: `SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_ROLE=SKYHOP_INGEST, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_PRIVATE_KEY_FILE=/secrets/rsa_key.p8`,
`PG*` for `postgres`. Mounts: `./keys:/secrets:ro`, `./generator/out:/app/generator/out:ro`.
Exit code 1 = a source failed → retry, then alert. All commands are replay-safe (retries never duplicate).
