#!/usr/bin/env bash
# Build the two images the DAG runs. From the REPO ROOT, after every code change:  bash scripts/build_images.sh
# The DAG always runs the IMAGE, not the code in your folder: no rebuild = old code.
set -euo pipefail
docker build -f ingestion/Dockerfile  -t skyhop-ingest:1.0.0 .    # Member 1's ingestion job
docker build -f docker/dbt/Dockerfile -t skyhop-dbt:1.0.0 .       # Member 2's dbt project
docker images | grep skyhop
