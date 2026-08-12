#!/usr/bin/env bash
set -euo pipefail

echo "== Loading raw data =="
python /opt/scripts/load_raw_to_warehouse.py

echo "== dbt deps =="
dbt deps

echo "== dbt seed =="
dbt seed --profiles-dir profiles --target docker

echo "== dbt run =="
dbt run --profiles-dir profiles --target docker

echo "== dbt test =="
dbt test --profiles-dir profiles --target docker

echo "== dbt docs generate =="
dbt docs generate --profiles-dir profiles --target docker

echo "== Pipeline init complete =="
