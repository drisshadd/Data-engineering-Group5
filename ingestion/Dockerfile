# skyhop-ingest · image of the Member 1 job, for Member 3's Airflow DAG (DockerOperator).
# Build from the repo root:  docker build -f ingestion/Dockerfile -t skyhop-ingest:1.0.0 .
FROM python:3.12.7-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/ingestion
WORKDIR /app
COPY ingestion/requirements.txt ingestion/requirements.txt
RUN pip install --no-cache-dir -r ingestion/requirements.txt
COPY ingestion/ ingestion/
COPY generator/messy_data.py generator/load_to_postgres.py generator/
COPY reference/ reference/
COPY docs/member1/bronze_expected_counts.json docs/member1/bronze_expected_counts.json
RUN useradd --create-home --uid 10001 skyhop && chown -R skyhop /app
USER skyhop
# secrets at run time only: -e SNOWFLAKE_* and -v ./keys:/secrets:ro (SNOWFLAKE_PRIVATE_KEY_FILE=/secrets/rsa_key.p8)
# data at run time: -v ./generator/out:/app/generator/out:ro
ENTRYPOINT ["python", "-m", "skyhop_ingest"]
CMD ["--help"]
