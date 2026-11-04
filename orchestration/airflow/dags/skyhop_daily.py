"""SkyHop Airlines · daily pipeline (Member 3).

    ingest_files ─────┐
    ingest_postgres ──┴──> verify_bronze ──┐
    ingest_apis ──> apis_finished ─────────┴──> dbt_build ──> notify_success
                    (runs even if ingest_apis failed: APIs are non-critical enrichment)

  ingest_files     source 1  flight-ops CSV drop  -> stage -> BRONZE.FLIGHTS / AIRPORTS        (COPY skips known files)
  ingest_postgres  source 2  reservation DB       -> BRONZE.BOOKINGS / PASSENGERS               (watermark in Snowflake)
  ingest_apis      sources 3-7 public APIs        -> BRONZE.API_RAW                             (MERGE on request key)
  verify_bronze    bronze rows per file == expected counts: the gate before dbt                 (exit 1 = stop)
  dbt_build        silver + quarantine + gold + 37 tests; a failed test skips everything downstream

Every task is a container (skyhop-ingest = Member 1, skyhop-dbt = Member 2). Airflow decides WHEN and IN WHAT
ORDER, retries, and alerts. Course reflexes: idempotent tasks (replay = same numbers), retries + alert after the
last one, failure visible (verify gate, dbt tests), schedule in the business time zone.
"""
import os
import sys

import pendulum

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # find skyhop_common.py next to this file
from airflow.sdk import DAG, Param, get_current_context, task

from skyhop_common import (GENERATOR_OUT, INGEST_KEY, POSTGRES_ENV, POSTGRES_SECRET, alert_on_failure,
                           dbt_task, ingest_task, post_to_webhook)

with DAG(
    dag_id="skyhop_daily",
    description="SkyHop: 3 sources -> bronze -> verify -> dbt (silver, quarantine, gold, tests)",
    # 06:00 London every day: the ops team reads the dashboard in the morning -> a daily batch is enough.
    schedule="0 6 * * *",
    start_date=pendulum.datetime(2026, 11, 1, tz="Europe/London"),
    catchup=False,
    max_active_runs=1,            # two runs never write the same tables at the same time
    default_args={
        "owner": "member3",
        "retries": 2,
        "retry_delay": pendulum.duration(seconds=30),
        "on_failure_callback": alert_on_failure,
    },
    tags=["skyhop"],
    params={
        "batch": Param(2, type="integer", enum=[1, 2],
                       description="Flight-ops file batch to load (1 = initial load, 2 = next day). "
                                   "verify only knows batches 1-2 (seed 42)."),
        "api_start": Param("2026-06-01", type="string", description="API window start (first booking)"),
        "api_end": Param("2026-09-30", type="string", description="API window end (last flight)"),
        "simulate_api_outage": Param(False, type="boolean",
                                     description="INCIDENT: Frankfurter API down -> retries, alert, dbt not run"),
    },
) as dag:

    ingest_files = ingest_task(
        "ingest_files",
        "files --batch {{ params.batch }}",
        mounts=(INGEST_KEY, GENERATOR_OUT),
    )

    ingest_postgres = ingest_task(
        "ingest_postgres",
        "postgres",
        extra_env=POSTGRES_ENV,
        secret_env=POSTGRES_SECRET,
    )

    ingest_apis = ingest_task(
        "ingest_apis",
        "apis --start {{ params.api_start }} --end {{ params.api_end }}"
        "{{ ' --simulate-outage frankfurter' if params.simulate_api_outage else '' }}",
    )

    verify_bronze = ingest_task("verify_bronze", "verify")

    dbt_build = dbt_task("dbt_build", "dbt build")

    # Public APIs (weather, FX, holidays) = NON-CRITICAL enrichment. If one is down, ingest_apis turns red and
    # alerts, but dbt still runs on the last good API_RAW rows (MERGE keeps them). dbt waits for the API task to
    # FINISH (success or failure) so it never reads API_RAW while it is being written.
    # Flight files + reservation DB = CRITICAL: if they fail, verify_bronze and dbt never run (upstream_failed).
    # Decision taken after a real Frankfurter outage (HTTP 522) on 4 Nov 2026.
    @task(trigger_rule="all_done")
    def apis_finished():
        print("ingest_apis has finished (success OR failure). If it is red, its alert was sent and dbt uses the "
              "last good API_RAW load. Critical sources are checked by verify_bronze.")

    @task
    def notify_success():
        ctx = get_current_context()
        post_to_webhook(f":large_green_circle: SkyHop pipeline OK ({ctx['run_id']}, batch {ctx['params']['batch']}): "
                        "bronze verified, dbt build passed, GOLD refreshed.")

    [ingest_files, ingest_postgres] >> verify_bronze
    [verify_bronze, ingest_apis >> apis_finished()] >> dbt_build >> notify_success()
