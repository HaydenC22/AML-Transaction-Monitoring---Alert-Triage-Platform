# ADR-0002: Full nightly refresh instead of incremental checkpoint-based ingestion

## Status
Accepted

## Context
The original design called for the Airflow DAG to slice the source file by
`step` (PaySim's hour offset) using a checkpoint table, so each `@daily` run
ingests "the next simulated day" — making a daily schedule meaningful rather
than theatrical, since the source is a static file, not a live feed.

Building that properly means: a `pipeline_state.ingestion_checkpoint` table,
watermark-advancing logic, append-not-truncate semantics throughout dbt, and
reprocessing/backfill handling if a run fails partway.

## Decision
`ingest_raw_slice` does a full idempotent reload of the entire source file on
every DAG run (`DROP ... CASCADE` + `COPY`), and every downstream dbt model is
a full rebuild (`table` materialization, not incremental).

## Consequences
- This is a real, common pattern for batch ELT at this data volume (~200K rows,
  builds in ~10 seconds) — full nightly refreshes are standard practice below a
  certain scale, not a shortcut unique to this MVP.
- The `@daily` schedule is honest about what it does (re-derive the full
  warehouse from source) rather than pretending to simulate incremental
  arrival of a static file.
- Trade-off made explicitly to control scope: incremental, checkpoint-based
  ingestion is the natural next step once this pipeline runs against a live,
  growing source rather than a fixed synthetic file — documented in the
  README's "what's next" rather than half-built here.
- Downstream effect worth naming: `detection.alerts` is also dropped and
  rebuilt with fresh serial IDs on every detection run, for the same reason.
  That means analyst dispositions (`app.alert_dispositions`, keyed by
  `alert_id`) don't durably survive a full pipeline re-run — a real limitation
  of a full-refresh design colliding with a stateful case-management workflow,
  and the natural companion piece to fix alongside incremental ingestion:
  giving alerts a stable natural key (e.g. `transaction_key` + rule set) instead
  of a regenerated surrogate one.
