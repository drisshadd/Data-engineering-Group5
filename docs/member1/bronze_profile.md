# Bronze profile — SkyHop (generator seed 42, 2 batches)

Produced by `python -m skyhop_ingest profile`. *bad shape* = present but not in the clean format expected for the column → a cleaning rule is needed in silver.

## airports — 20 rows

Files: batch_001/airports.csv (18 rows); batch_002/airports.csv (2 rows)

| Column | Missing (empty/N/A/null/-) | Bad shape | Distinct | Examples to clean | First seen |
|---|---|---|---|---|---|
| airport_code | 0 | 0 | 19 | — | batch_001 |
| city | 0 | 0 | 10 | — | batch_001 |
| runways | 0 | 0 | 3 | — | batch_001 |

## bookings — 9496 rows

Files: batch_001/bookings.csv (7224 rows); batch_002/bookings.csv (2272 rows)

| Column | Missing (empty/N/A/null/-) | Bad shape | Distinct | Examples to clean | First seen |
|---|---|---|---|---|---|
| booking_id | 0 | 0 | 9100 | — | batch_001 |
| flight_id | 52 | 0 | 1015 | — | batch_001 |
| passenger_id | 62 | 0 | 3005 | — | batch_001 |
| fare_gbp | 66 | 243 | 8156 | `-71.74`, `€60.79`, `-172.8`, `-250.24` | batch_001 |
| cabin | 51 | 199 | 15 | `BUSINESS`, `PREMIUM`, `ECONOMY`, `' premium '` | batch_001 |
| booked_at | 44 | 214 | 6915 | `2026-09-18T13:48:22+01:00`, `2026-08-17T15:58:42+01:00`, `1782157510`, `2026-06-14T02:25:50+01:00` | batch_001 |
| booked_at_v2 | 9 | 71 | 2187 | `1784896753`, `2026-06-27 08:48:24`, `2026-06-06 09:24:13`, `2026-07-16T00:43:13+01:00` | batch_002 |
| source_system | 0 | 0 | 3 | — | batch_002 |

## flights — 976 rows

Files: batch_001/flights.csv (928 rows); batch_002/flights.csv (48 rows)

| Column | Missing (empty/N/A/null/-) | Bad shape | Distinct | Examples to clean | First seen |
|---|---|---|---|---|---|
| flight_id | 0 | 0 | 945 | — | batch_001 |
| flight_number | 10 | 36 | 648 | `sh874`, `sh954`, `'  SH706'`, `sh815` | batch_001 |
| origin | 4 | 4 | 23 | `AP003X`, `AP002X`, `AP004X`, `AP005X` | batch_001 |
| destination | 6 | 8 | 25 | `AP013X`, `AP004X`, `AP007X`, `AP005X` | batch_001 |
| scheduled_departure | 5 | 29 | 938 | `2026-09-12T18:47:22+01:00`, `2026-09-22 02:24:46`, `1789196517`, `2026-09-08T03:06:52+01:00` | batch_001 |
| delay_min | 6 | 16 | 259 | `-63`, `-47`, `-195`, `' 5 '` | batch_001 |
| seats | 6 | 13 | 140 | `' 177 '`, `' 156 '`, `138 units`, `-98` | batch_001 |

## passengers — 3257 rows

Files: batch_001/passengers.csv (3096 rows); batch_002/passengers.csv (161 rows)

| Column | Missing (empty/N/A/null/-) | Bad shape | Distinct | Examples to clean | First seen |
|---|---|---|---|---|---|
| passenger_id | 0 | 0 | 3150 | — | batch_001 |
| full_name | 23 | 0 | 632 | — | batch_001 |
| email | 19 | 74 | 3116 | `' noah.hall12@icloud.com'`, `lily.hall7proton.me`, `finley.hall51proton.me`, `LEO.DAVIES4@PROTON.ME` | batch_001 |
| frequent_flyer_tier | 19 | 82 | 19 | `PLATINUM`, `SILVER`, `NONE`, `GOLD` | batch_001 |

## Issues injected by the generator (ground truth, `issues_report.json`)

| Issue | Count |
|---|---|
| category: inconsistent spelling / case / spaces / translation | 403 |
| row: exact duplicate | 214 |
| row: near duplicate (same id, a field differs) | 206 |
| foreign key: orphan id that does not exist in the parent table | 180 |
| datetime: time zone offset instead of UTC (+01:00) | 173 |
| datetime: other formats (local time without zone, epoch seconds, dd/mm/yyyy hh:mm) | 130 |
| money: text with currency symbol / thousands separator / comma decimal | 129 |
| fk: missing value as empty / N/A / null text | 123 |
| email: invalid or inconsistent (no @, upper case, spaces, test address) | 118 |
| row: update of a row sent in an earlier batch (same id, new values) | 115 |
| money: negative amount (refund encoded as negative, or sign error) | 104 |
| money: outlier x100 (pence instead of pounds) | 97 |
| person: broken encoding (Ã© instead of é) | 83 |
| datetime: impossible future date (year 2099) or 1970 default | 81 |
| category: missing value as empty / N/A / null text | 67 |
| money: missing value as empty / N/A / null text | 62 |
| datetime: missing value as empty / N/A / null text | 56 |
| person: wrong case / extra spaces / LAST, First | 51 |
| text: extra spaces / case | 47 |
| int: number stored as text with spaces or units | 35 |
| person: missing value as empty / N/A / null text | 23 |
| int: outlier / impossible value (negative or x1000) | 21 |
| email: missing value as empty / N/A / null text | 17 |
| int: missing value as empty / N/A / null text | 12 |
| text: missing value as empty / N/A / null text | 10 |
| schema drift: bookings.booked_at renamed to booked_at_v2 and column source_system added (batch 2) | 1 |
