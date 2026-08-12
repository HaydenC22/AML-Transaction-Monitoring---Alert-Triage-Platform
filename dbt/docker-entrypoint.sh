#!/usr/bin/env bash
set -euo pipefail

echo "== Loading raw data =="
python /opt/scripts/load_raw_to_warehouse.py

echo "== dbt deps =="
dbt deps

echo "== dbt seed =="
dbt seed --profiles-dir profiles --target docker

echo "== dbt run (staging/intermediate/marts.core) =="
dbt run --select staging intermediate marts.core --profiles-dir profiles --target docker

echo "== dbt test (staging/intermediate/marts.core) =="
# --indirect-selection=cautious: without it, dbt's default "eager" mode also runs
# cross-layer relationship tests owned by marts.detection models (e.g. fct_alerts ->
# fact_transactions) purely because fact_transactions is in scope, even though
# fct_alerts itself isn't -- and detection.alerts doesn't exist yet at this point
# in the pipeline (see docker-compose.yml's detection-init service, which runs after).
dbt test --select staging intermediate marts.core --indirect-selection=cautious --profiles-dir profiles --target docker

echo "== dbt docs generate =="
dbt docs generate --profiles-dir profiles --target docker

echo "== Pipeline init complete =="
