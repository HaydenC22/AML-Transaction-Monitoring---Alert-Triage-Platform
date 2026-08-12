# ADR-0001: Two Postgres containers instead of one shared instance

## Status
Accepted

## Context
Airflow needs a metadata database (DAG state, task instances, connections). The
platform also needs an analytics warehouse (star schema, detection output, app
state). Both are Postgres. Running one shared instance would save a container.

## Decision
Run two separate Postgres containers: `pg-airflow` (Airflow's metadata DB only)
and `pg-warehouse` (the AML analytics warehouse — `raw`, `raw_staging`,
`raw_intermediate`, `raw_marts_core`, `raw_marts_detection`, `detection`,
`app`, and `pipeline_state` schemas).

## Consequences
- An analytical query or a runaway `dbt run` against the warehouse cannot lock
  or corrupt Airflow's own scheduling state — the two systems have genuinely
  different access patterns (Airflow: many small transactional writes; warehouse:
  occasional large batch rebuilds) and no reason to share blast radius.
- The warehouse container's schema stays clean of Airflow-internal tables,
  which matters for the hosted demo split (ADR-0005): only the warehouse schema
  needs to be mirrored into Neon, with no Airflow tables to filter out or expose.
- Cost: one extra Postgres container locally. Negligible — both are `postgres:16-alpine`
  and idle most of the time.
