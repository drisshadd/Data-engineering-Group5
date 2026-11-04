"""Shared settings for the SkyHop DAGs (Member 3). Everything comes from orchestration/airflow/.env.

Not a DAG itself: Airflow puts the dags/ folder on the Python path, so the DAG files import it.
"""
import json
import os
import urllib.request

from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount


def setting(name, default=None):
    value = os.environ.get(name, default)
    if value in (None, ""):
        # Shows up as a red "DAG import error" banner in the UI: a missing setting is visible, never silent.
        raise ValueError(f"{name} is missing in orchestration/airflow/.env (then: docker compose up -d)")
    return value


INGEST_IMAGE = "skyhop-ingest:1.0.0"   # Member 1: ingestion/Dockerfile
DBT_IMAGE = "skyhop-dbt:1.0.0"         # Member 2's dbt project: docker/dbt/Dockerfile
NETWORK = "skyhop-net"                 # created by docker-compose.yml; Postgres is "skyhop-postgres" on it

# Host paths (absolute, on the Mac): the task containers are started by Docker Desktop, so they mount host paths.
INGEST_KEY = Mount(source=setting("INGEST_KEY_FILE"), target="/secrets/rsa_key.p8", type="bind", read_only=True)
GENERATOR_OUT = Mount(source=setting("GENERATOR_OUT_DIR"), target="/app/generator/out", type="bind", read_only=True)

INGEST_ENV = {
    "SNOWFLAKE_ACCOUNT": setting("SNOWFLAKE_ACCOUNT"),
    "SNOWFLAKE_USER": setting("INGEST_SNOWFLAKE_USER", "SKYHOP_INGEST_SVC"),
    "SNOWFLAKE_ROLE": "SKYHOP_INGEST",
    "SNOWFLAKE_WAREHOUSE": "SKYHOP_WH",
    "SNOWFLAKE_PRIVATE_KEY_FILE": "/secrets/rsa_key.p8",
}
POSTGRES_ENV = {
    "PGHOST": "skyhop-postgres",       # container name on skyhop-net
    "PGPORT": "5432",
    "PGUSER": setting("PGUSER"),
    "PGDATABASE": setting("PGDATABASE"),
}
# Secrets go in private_environment: passed to the container but never shown in the Airflow UI.
POSTGRES_SECRET = {"PGPASSWORD": setting("PGPASSWORD")}

DBT_TARGET = os.environ.get("DBT_TARGET", "keypair")
DBT_ENV = {
    "SNOWFLAKE_ACCOUNT": setting("SNOWFLAKE_ACCOUNT"),
    "SNOWFLAKE_USER": setting("DBT_SNOWFLAKE_USER", "DBT_SVC"),
    "DBT_TARGET": DBT_TARGET,
    "SNOWFLAKE_PRIVATE_KEY_FILE": "/secrets/rsa_key.p8",
}
if DBT_TARGET == "keypair":
    DBT_MOUNTS = [Mount(source=setting("DBT_KEY_FILE"), target="/secrets/rsa_key.p8", type="bind", read_only=True)]
    DBT_SECRET = {}
else:
    DBT_MOUNTS = []
    DBT_SECRET = {"SNOWFLAKE_PASSWORD": setting("DBT_SNOWFLAKE_PASSWORD")}


def post_to_webhook(text):
    """Slack and Teams workflows both accept {"text": "..."}. No URL set -> printed in the task log."""
    url = os.environ.get("ALERT_WEBHOOK_URL")
    if not url:
        print("ALERT (no ALERT_WEBHOOK_URL set):", text)
        return
    req = urllib.request.Request(url, data=json.dumps({"text": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)


def alert_on_failure(context):
    """on_failure_callback: fires after the LAST retry (course pack 07-data-quality-and-alerting)."""
    ti = context["task_instance"]
    post_to_webhook(f":red_circle: SkyHop: *{ti.dag_id}.{ti.task_id}* FAILED for {context['ds']} "
                    f"after {ti.try_number} attempts. Logs: {ti.log_url}")


def ingest_task(task_id, command, mounts=(INGEST_KEY,), extra_env=None, secret_env=None, **kwargs):
    """One Member 1 command = one container (image entrypoint: python -m skyhop_ingest)."""
    return DockerOperator(
        task_id=task_id,
        image=INGEST_IMAGE,
        command=command,
        environment={**INGEST_ENV, **(extra_env or {})},
        private_environment=secret_env or {},
        mounts=list(mounts),
        network_mode=NETWORK,
        mount_tmp_dir=False,
        auto_remove="success",       # a failed container is kept: `docker logs` for debugging
        **kwargs,
    )


def dbt_task(task_id, command):
    return DockerOperator(
        task_id=task_id,
        image=DBT_IMAGE,
        command=command,
        environment=DBT_ENV,
        private_environment=DBT_SECRET,
        mounts=DBT_MOUNTS,
        network_mode=NETWORK,
        mount_tmp_dir=False,
        auto_remove="success",
    )
