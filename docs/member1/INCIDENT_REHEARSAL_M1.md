# Incident rehearsal — Member 1 part (Phase 4)

Member 1 owns the **source side** of the incidents: inject the problem, show bronze behaves, hand the
detection to M2 (DQ checks) and M3 (DAG alert). Rehearse each one twice; target ≤ 90 s each on demo day.

## Incident B · Replay / double delivery (TESTED, live on Snowflake) — 60 s
Story: "the flight-ops team re-sent yesterday's files and Airflow retried the task."
```bash
python -m skyhop_ingest verify                       # before: 8 files OK, 13,749 rows
python -m skyhop_ingest files --batch 1              # replay
python -m skyhop_ingest reservations-files --batch 1 # (or: postgres -> 'new batches=none')
python -m skyhop_ingest verify                       # after: identical
```
Say: "PUT says SKIPPED, COPY says 0 files processed: Snowflake keeps 64 days of load history.
The watermark only moves after a successful COPY. Bronze never double counts, so gold cannot."
Offline proof: `tests/member1/test_bronze.py` (no OVERWRITE, no FORCE, watermark order, verify detects doubling).

## Incident C · Public API down (TESTED offline, live demo optional) — 45 s
Story: "the ECB rates API is unreachable at 06:00."
```bash
python -m skyhop_ingest apis --simulate-outage frankfurter ; echo "exit code: $?"
```
Expected log: 3 attempts with back-off on `outage.invalid`, `frankfurter FAILED`, the 4 other sources
merged, **exit code 1** → Airflow retries then alerts (M3). Gold keeps the last stored rates.
Offline proof: `tests/member1/test_apis.py::test_incident_c_api_outage_others_still_loaded`.

## Incident A · Corrupted daily feed (M1 injects, M2 detects) — 30 s for my part
Story: "the reservation system sends a broken day."
```bash
python generator/messy_data.py --company skyhop --mess high --seed 7 --out /tmp/bad
python -m skyhop_ingest reservations-files --data /tmp/bad/skyhop --batch 1 --as-batch 3
python -m skyhop_ingest verify ; echo "exit code: $?"     # batch_003 = NOT EXPECTED -> exit 1
```
Then hand over: "bronze accepted it (bronze never rejects) and flags an unexpected file; M2's quarantine
rate check fails, the DAG stops before publishing gold."
Recovery (after M2's part):
```sql
REMOVE @SKYHOP.BRONZE.LANDING PATTERN = '.*batch_003/.*';
DELETE FROM SKYHOP.BRONZE.BOOKINGS   WHERE _source_file LIKE '%batch_003/%';
DELETE FROM SKYHOP.BRONZE.PASSENGERS WHERE _source_file LIKE '%batch_003/%';
```
then `verify` → all OK again.

## Rehearsal checklist
- [ ] Terminal font ≥ 18 pt, commands pre-typed in a script, Snowsight tab open on `02_bronze_checks.sql`
- [ ] Screenshots of each incident saved in `docs/evidence/member1/` (backup if Wi-Fi fails)
- [ ] Timed run: B ____ s · C ____ s · A ____ s
- [ ] Hand-over sentence to M2 and M3 agreed
