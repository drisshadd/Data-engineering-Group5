# Orchestration – Airflow + Docker + PostgreSQL (Member 3)

```
                 ┌──────────── docker compose (orchestration/airflow) ─────────────┐
                 │  skyhop-airflow (UI :8080, scheduler)    skyhop-postgres (:5433)  │
                 └───────────┬──────────────────────────────────▲───────────────────┘
                             │ starts one container per task     │ reservation DB
                             ▼  (network skyhop-net)             │
 skyhop_daily:  ingest_files ─────┐
                ingest_postgres ──┴──> verify_bronze ──┐
                ingest_apis ──> apis_finished ─────────┴──> dbt_build ──> notify_success
                (APIs = non-critical: red + alert, but dbt still runs on the last good API data)
                (skyhop-ingest image = Member 1)       (skyhop-dbt image = Member 2)
```

| DAG | What it does |
|---|---|
| `skyhop_daily` | The pipeline. 06:00 Europe/London. 3 ingestion tasks in parallel → bronze gate → dbt build (16 models + 37 tests) → success message. 2 retries per task, alert after the last one. |
| `skyhop_source_simulator` | **Not** the pipeline: plays the reservation application and writes a generator batch into Postgres, so `ingest_postgres` has a real source to read. |

Logins (key pairs, no password in any file): ingestion = `SKYHOP_INGEST_SVC` / role `SKYHOP_INGEST`,
dbt = `DBT_SVC` / role `SKYHOP_TRANSFORM`. Keys stay in `~/.snowflake/` on the Mac and are mounted read-only into
the task containers at run time; they are never in an image or in Git. Secrets passed as environment variables use
`private_environment`, so the Airflow UI never shows them.

---

## Step by step (first time ≈ 45 min, mostly downloads)

All commands from the **repo root** unless written otherwise.

### 1 · Generate the source files (same seed as Member 1)
```bash
python3 generator/messy_data.py --company skyhop --batches 2 --seed 42 --out generator/out
ls generator/out/skyhop          # batch_001  batch_002  issues_report.json
```

### 2 · Build the two task images
```bash
bash scripts/build_images.sh     # skyhop-ingest:1.0.0 (Member 1) + skyhop-dbt:1.0.0 (Member 2)
```

### 3 · Settings
```bash
cd orchestration/airflow
cp .env.example .env
echo $HOME                       # /Users/<you>: use it in the paths of .env ("~" does not work there)
```
Fill `.env`: the two key files, the absolute path of `generator/out`. Keep the Postgres lab values.

### 4 · Start Airflow + Postgres
```bash
docker compose up -d --build     # first time: a few minutes
docker compose ps                # skyhop-postgres "healthy", skyhop-airflow "running"
```
Wait ~1 minute, open http://localhost:8080. Both DAGs are listed; no red "import error" banner.

### 5 · Smoke tests (1 command each, before the first DAG run)
```bash
# ingestion login + Snowflake + bronze gate (read-only): expect 8 lines "OK"
docker run --rm -e SNOWFLAKE_ACCOUNT=DQYYEIS-EW25504 -e SNOWFLAKE_USER=SKYHOP_INGEST_SVC \
  -e SNOWFLAKE_ROLE=SKYHOP_INGEST -e SNOWFLAKE_WAREHOUSE=SKYHOP_WH -e SNOWFLAKE_PRIVATE_KEY_FILE=/secrets/rsa_key.p8 \
  -v ~/.snowflake/ingest_m3_key.p8:/secrets/rsa_key.p8:ro skyhop-ingest:1.0.0 verify

# dbt login: expect "All checks passed!"
docker run --rm -e SNOWFLAKE_ACCOUNT=DQYYEIS-EW25504 -e SNOWFLAKE_USER=DBT_SVC \
  -e SNOWFLAKE_PRIVATE_KEY_FILE=/secrets/rsa_key.p8 \
  -v ~/.snowflake/dbt_svc_key.p8:/secrets/rsa_key.p8:ro skyhop-dbt:1.0.0 dbt debug
```

### 6 · Fill the reservation database (Postgres)
UI → `skyhop_source_simulator` → **Trigger** with `batch = 1`, then again with `batch = 2`. Check:
```bash
docker exec skyhop-postgres psql -U source -d project_source \
  -c "SELECT _batch, COUNT(*) FROM skyhop.bookings GROUP BY 1 ORDER BY 1"
```

### 7 · First full run
UI → `skyhop_daily` → **unpause** (toggle) → **Trigger** (default `batch = 2`). All 6 tasks go green (≈ 3–5 min).
What the logs show, and what to say:
- `ingest_files`: PUT/COPY "skipped" → files already loaded: **COPY load history makes the replay safe**.
- `ingest_postgres`: `watermark=2 new batches=none` → Member 1 already loaded batches 1–2: **the watermark works**.
- `ingest_apis`: `API_RAW: N documents merged` → **MERGE on the request key: no duplicate**.
- `verify_bronze`: 8 files `OK` → the bronze gate.
- `dbt_build`: `PASS=53` → same numbers as Member 2's manual baseline (`dbt/reconciliation.sql`).

### 8 · Idempotency proof
Trigger again with the same settings → all green, and `dbt/reconciliation.sql` gives the same numbers
(866 flights, 8,123 bookings, 79 + 977 quarantined, £1,788,710.02).

### 9 · Incident 1 – the reservation database is down (real Docker + Postgres failure)
```bash
docker stop skyhop-postgres
```
Trigger `skyhop_daily` → `ingest_postgres` fails, retries 2× (30 s apart), turns **red**, alert in its log
(or Slack); `verify_bronze` and `dbt_build` = **upstream_failed**: nothing reaches GOLD, the dashboard keeps
yesterday's correct numbers.
Recovery:
```bash
docker start skyhop-postgres
```
UI → click `ingest_postgres` → **Clear task** (downstream included) → run finishes green. The watermark only
moves after a successful COPY, so nothing is lost or duplicated.

### 10 · Incident 2 – a public API is down (happened FOR REAL on 4 Nov 2026: Frankfurter HTTP 522)
`ingest_apis`: Frankfurter fails 3× inside the job, the 4 other APIs are still loaded, exit code 1 → Airflow
retries 2× → **red** + alert. `apis_finished` then lets the run continue: `verify_bronze` (critical sources) and
`dbt_build` run on the last good API data (MERGE kept it), GOLD is refreshed. To replay it on purpose: trigger
with `simulate_api_outage = true`.
Design decision to explain: **critical** sources (flight files, reservation DB) block the run; **enrichment**
sources (weather, FX, holidays) alert but do not block, because yesterday's FX rate is still a correct input.

### 11 · Evidence for the slides (`docs/evidence/member3/`)
Graph view all green · Graph view incident 1 (red + upstream_failed) · alert line in the log · `dbt_build` log
with `PASS=53` · `docker compose ps` · Postgres query of step 6.

### 12 · Commit
```bash
git add orchestration docker scripts .dockerignore docs/evidence/member3
git status                       # .env, *.p8, generator/out must NOT be listed
git commit -m "M3: Airflow DAG (Docker + Postgres), dbt image, incidents"
git push
```

Stop everything after the demo: `docker compose down` (data kept) or `docker compose down -v` (Postgres wiped).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Red "DAG import error": `... is missing in orchestration/airflow/.env` | Fill that line in `.env`, then `docker compose up -d` (restart picks it up). |
| `pull access denied for skyhop-ingest` / `skyhop-dbt` | Images not built: step 2. |
| `JWT token is invalid` | The key file is not the one registered on that Snowflake user. Member 1 (ACCOUNTADMIN) runs `ALTER USER <user> SET RSA_PUBLIC_KEY_2 = '<your .pub body>'` (file B of yesterday). |
| `User 'DBT_SVC' does not exist` | Member 1 did not create it yet (file B §3). Meanwhile: `DBT_TARGET=password` + the login you used for `dbt build` in `.env`. |
| `network skyhop-net not found` | Start the compose first (step 4): it creates the network. |
| `Mounts denied` | Docker Desktop → Settings → Resources → File sharing: add `/Users`. |
| `could not translate host name "skyhop-postgres"` | Postgres container stopped (incident 1) or compose not running. |
| `verify_bronze` NOT EXPECTED / MISMATCH | Someone loaded a batch that is not 1–2 (seed 42). Only batches 1 and 2 exist in the expected counts. |
| Code changed but the task does the old thing | Rebuild the images (step 2). |

## What to say about the choices

- **Airflow + DockerOperator**: each step is a versioned image (`1.0.0`) with pinned dependencies; Airflow only
  schedules, orders, retries and alerts. Same images would run on Kubernetes (`KubernetesPodOperator`) in production.
- **Daily batch at 06:00 London**: the decision (ops review) is daily → batch, not streaming.
- **Idempotent tasks**: COPY load history, watermark moved only after success, MERGE for APIs, dbt rebuilds →
  a retry or a replay never duplicates. Proven in step 8.
- **Failure is visible**: retries for transient errors, alert after the last retry, `verify_bronze` gate and 37 dbt
  tests stop bad data before GOLD.
- **Least privilege**: ingestion robot can only write BRONZE; dbt robot only builds SILVER/GOLD/QUARANTINE;
  dashboard role reads GOLD only.
- **Known shortcuts (say them)**: Airflow runs as root to use the Docker socket (laptop only); Airflow's own
  metadata is SQLite in standalone mode; the Postgres password is a throw-away lab value.
