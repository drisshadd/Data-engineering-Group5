"""SkyHop · SOURCE SIMULATOR (not part of the pipeline).

Plays the airline's reservation application: it writes one day of bookings and passengers (a generator batch)
into the Postgres "on-prem" database. The pipeline (skyhop_daily) then picks them up with its watermark.

  batch 1 = initial load (tables recreated)     batch 2 = next day (appended: new rows, updates, schema drift)

Run batch 1 once, then batch 2 once. Uses generator/load_to_postgres.py from Member 1's image.
"""
import os
import sys

import pendulum

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # find skyhop_common.py next to this file
from airflow.sdk import DAG, Param

from skyhop_common import GENERATOR_OUT, POSTGRES_ENV, POSTGRES_SECRET, ingest_task

with DAG(
    dag_id="skyhop_source_simulator",
    description="Simulates the reservation system: writes a generator batch into Postgres",
    schedule=None,                       # manual trigger only
    start_date=pendulum.datetime(2026, 11, 1, tz="Europe/London"),
    catchup=False,
    max_active_runs=1,
    tags=["skyhop", "simulation"],
    params={"batch": Param(1, type="integer", enum=[1, 2], description="1 first, then 2")},
) as dag:

    ingest_task(
        "write_batch_into_postgres",
        "generator/load_to_postgres.py --company skyhop --batch {{ params.batch }} --data generator/out"
        "{{ ' --append' if params.batch > 1 else '' }}",
        mounts=(GENERATOR_OUT,),
        extra_env=POSTGRES_ENV,
        secret_env=POSTGRES_SECRET,
        entrypoint=["python"],           # the image's default entrypoint is `python -m skyhop_ingest`
        retries=0,
    )
