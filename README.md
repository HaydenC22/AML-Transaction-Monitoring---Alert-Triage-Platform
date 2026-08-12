# AML Transaction Monitoring & Alert Triage Platform

> **Status: work in progress.** This README is a placeholder scaffold updated as each build phase lands
> (see `docs/adr/` for design decisions made so far). Full problem statement, architecture diagram,
> run instructions, screenshots, and metrics will replace this section once the pipeline, detection
> engine, API, and frontend are complete.

## Synthetic data disclaimer

All transaction data in this repository is synthetically generated (schema-compatible with the public
[PaySim](https://www.kaggle.com/datasets/ealaxi/paysim1) dataset — see `data/sample/DATA_DICTIONARY.md`).
No production or personal data is used anywhere in this project.

## What this is

A hybrid rules + machine-learning AML transaction monitoring pipeline and analyst alert-triage platform,
covering the full stack from data ingestion through detection to a case-management dashboard. Built as
a portfolio project demonstrating modern data engineering (Airflow, dbt, Great Expectations), applied ML
in production (Isolation Forest + deterministic rules), and product/BI thinking (analyst triage queue,
BA artifacts, metrics dashboard).

## Repository layout

| Path | Purpose |
|---|---|
| `airflow/` | Orchestration DAG |
| `dbt/` | Star-schema transformations |
| `great_expectations/` | Data-quality suites |
| `detection/` | Rules engine + Isolation Forest + evaluation |
| `api/` | FastAPI backend for the triage dashboard |
| `frontend/` | React + TypeScript dashboard |
| `docs/adr/` | Architecture decision records |
| `docs/ba/` | Business-analysis artifacts (process map, user stories, PRD) |
| `docs/metrics/` | Generated evaluation reports |

Full run instructions land once `docker-compose.yml` and the pipeline are wired end-to-end (tracked in
the project's build plan).
