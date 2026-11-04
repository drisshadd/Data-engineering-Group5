# skyhop-dbt · runs Member 2's dbt project (bronze -> silver / quarantine -> gold + 37 tests) for the Airflow DAG.
# Build from the REPO ROOT:  docker build -f docker/dbt/Dockerfile -t skyhop-dbt:1.0.0 .
FROM python:3.12.7-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DBT_PROFILES_DIR=/app

WORKDIR /app

# 1. dependencies first (cached layer)
COPY docker/dbt/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# 2. the dbt project + a profile that reads everything from environment variables (no secret in the image)
COPY dbt/ ./
COPY docker/dbt/profiles.yml ./profiles.yml
RUN if [ -f packages.yml ]; then dbt deps; fi

# 3. non-root user; dbt writes target/ and logs/ so it must own /app
RUN useradd --create-home --uid 1000 skyhop && chown -R skyhop /app
USER skyhop

CMD ["dbt", "build"]
