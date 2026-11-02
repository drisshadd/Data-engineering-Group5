# Member 1 · Data, APIs, Bronze, Dashboard — step by step (macOS, zsh)

Your column of the plan, in order. Every step ends with a ✅ check you can screenshot.

| Phase | Your tasks | Files |
|---|---|---|
| 1 | Generate data · test APIs · start bronze | `generator/`, `ingestion/`, `snowflake/bronze/` |
| 2 | Bronze finished → hand over to M2 | `docs/member1/HANDOVER_TO_M2.md`, `bronze_profile.md` |
| 3 | Dashboard on gold | `dashboard/` |
| 4 | Rehearse incident | `docs/member1/INCIDENT_REHEARSAL_M1.md` |
| End | Your slides + full rehearsals | `slides/member1_*.pptx` |

## 0. Setup (once)
```bash
cd Data-engineering-Group5
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-member1-dev.txt
cp .env.member1.example .env               # fill SNOWFLAKE_ACCOUNT (org-account)
cat .gitignore.member1 >> .gitignore
export PYTHONPATH=ingestion
set -a && source .env && set +a
python -m pytest -q tests/member1          # ✅ 16 passed
```

## Phase 1
**1.1 Generate the data** (seed 42 → the whole group gets identical files)
```bash
python -m skyhop_ingest generate           # ✅ total rows: 13749 · writes docs/member1/bronze_expected_counts.json
```
**1.2 Test the 5 APIs live**
```bash
python -m skyhop_ingest check-apis         # ✅ 5 × OK → docs/member1/api_check_report.md (commit it: evidence)
```
If one fails: re-run once; if it still fails, note it in the report — the job is built to continue without it.

**1.3 Bronze objects** (needs database `SKYHOP` + warehouse `SKYHOP_WH` from M3)
- Keys: `mkdir -p keys && openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out keys/rsa_key.p8 -nocrypt && openssl rsa -in keys/rsa_key.p8 -pubout -out keys/rsa_key.pub`
- Snowsight worksheet: run `snowflake/bronze/00_ingest_access.sql` (only missing parts, ask M3), then
  `ALTER USER SKYHOP_INGEST_SVC SET RSA_PUBLIC_KEY='<rsa_key.pub body without BEGIN/END>';`
- Run `snowflake/bronze/01_bronze_objects.sql`.

**1.4 Source 2 = PostgreSQL (reservation system)**
```bash
docker compose -f docker-compose-databases.yml up -d postgres      # course file: user source / source_pw
python generator/load_to_postgres.py --company skyhop --batch 1 --data generator/out
```
(No Docker? skip; use `reservations-files` below — say it in the defence.)

## Phase 2 — load bronze, prove it, hand over
```bash
python -m skyhop_ingest files --batch 1                 # source 1: flight-ops files
python -m skyhop_ingest postgres                         # source 2: watermark → batch 1
#   fallback without PostgreSQL:  python -m skyhop_ingest reservations-files --batch 1
python -m skyhop_ingest apis                             # sources 3-7 → API_RAW
# day 2 (late rows, updates, schema drift):
python generator/load_to_postgres.py --company skyhop --batch 2 --data generator/out --append
python -m skyhop_ingest files --batch 2
python -m skyhop_ingest postgres                         # ✅ 'new batches=[2]'
python -m skyhop_ingest verify                           # ✅ 8 files OK · API_RAW 5 sources
python -m skyhop_ingest profile                          # ✅ docs/member1/bronze_profile.md
```
Run `snowflake/bronze/02_bronze_checks.sql` → screenshots into `docs/evidence/member1/`.
Tick the table at the top of `HANDOVER_TO_M2.md`, push, send M2 the link.

## Phase 3 — dashboard on gold
```bash
streamlit run dashboard/app.py                           # offline now (expected gold sample)
SKYHOP_DASH_SOURCE=snowflake SNOWFLAKE_ROLE=SKYHOP_ANALYST SNOWFLAKE_USER=<your user> \
  SNOWFLAKE_PRIVATE_KEY_FILE=keys/<your key>.p8 streamlit run dashboard/app.py    # when M2's gold exists
```
✅ The 6 tiles show 866 · 7.2 % · 118 min · £1,788,710 · 7.0 % · £419,540 on both sources (acceptance test).
Cloud option (no laptop needed on demo day): Snowsight › Projects › Streamlit › + Streamlit App, role
`SKYHOP_ANALYST`, warehouse `SKYHOP_WH`, paste `dashboard/app.py` (altair and pandas are available there).

## Phase 4 — incidents
Follow `INCIDENT_REHEARSAL_M1.md` (B replay, C API outage, A corrupted feed injection).

## Push to the group repo
```bash
git checkout -b member1-ingestion-bronze-dashboard
git add ingestion snowflake/bronze dashboard tests docs/member1 generator reference tools slides \
        requirements-member1-dev.txt .env.member1.example .gitignore
git commit -m "Member 1: data, API checks, bronze ingestion, handover, dashboard, incident rehearsal"
git push -u origin member1-ingestion-bronze-dashboard     # then open a Pull Request
```
Never commit `.env`, `keys/`, `generator/out/`.

## What is verified where
| Claim | Verified offline (here) | You verify on Snowflake |
|---|---|---|
| Expected bronze counts | ✅ 13,749 rows / 8 files | `verify` = all OK |
| API validators, retries, outage | ✅ fixtures + mocks | `check-apis` 5 × OK |
| Replay-safe statements, watermark | ✅ fake cursor | incident B live |
| Dashboard numbers | ✅ AppTest on expected gold | same tiles on M2's gold |
| SQL syntax, Snowflake privileges | ❌ not executable here | run 00 → 02 |

`tools/reference_gold/` = small offline implementation used only to produce the expected gold sample for
the dashboard; Member 2's dbt models are the real silver/gold.

## Live-run notes (2 Nov 2026)
- PostgreSQL: port 5432 was taken on the Mac, so the source DB runs as its own container on 5433:
  `docker run -d --name skyhop-pg -e POSTGRES_USER=source -e POSTGRES_PASSWORD=source_pw -e POSTGRES_DB=project_source -p 5433:5432 postgres:16`
- SNOWFLAKE_ACCOUNT: use the value of `SELECT CURRENT_ORGANIZATION_NAME() || '-' || CURRENT_ACCOUNT_NAME();`
- Register the key as ACCOUNTADMIN (SYSADMIN cannot ALTER USER); check RSA_PUBLIC_KEY_FP with DESC USER.
- Run evidence queries on warehouse SKYHOP_WH (not another lab warehouse) so project costs stay separate.
