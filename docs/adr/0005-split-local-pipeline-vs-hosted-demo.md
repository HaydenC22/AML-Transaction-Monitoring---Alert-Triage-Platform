# ADR-0005: Split local full pipeline vs. lightweight hosted demo

## Status
Accepted

## Context
The "live demo" engineering standard expects a working deployed link. The
full pipeline (Airflow, dbt, Great Expectations, the detection engine, two
Postgres instances) isn't something free hosting tiers run well continuously
— Airflow alone needs a persistent scheduler process and its own metadata DB,
which pushes past what free tiers like Render's are meant for, and paying to
host an orchestrator for a portfolio piece isn't worth the ongoing cost.

## Decision
Split the deployment story in two:
- **Local, full-fidelity:** `docker compose up` runs the entire pipeline —
  ingestion, dbt, Great Expectations, detection, Airflow orchestration — for a
  reviewer to inspect end-to-end, including triggering the DAG themselves.
- **Hosted, lightweight:** the React dashboard (Vercel) and FastAPI backend
  (Render free tier) deploy against a small hosted Postgres (Neon free tier),
  kept fresh by a scheduled GitHub Action that reruns the same dbt +
  detection + evaluation sequence against the committed sample dataset and
  pushes the result into Neon — without ever running Airflow itself in the
  cloud.

## Consequences
- The hosted demo link is a real, working product surface — not a static
  screenshot — genuinely free to run indefinitely.
- It isn't "live" in the continuous-ingestion sense; it refreshes on the
  GitHub Action's schedule rather than reacting to new data in real time.
  That's disclosed in the README rather than implied otherwise.
- Two free-tier constraints worth documenting rather than hiding: Neon's
  compute scales to zero after 5 minutes idle (~1s cold start on the next
  query — negligible); Render's free web service spins down after 15 minutes
  idle (30-60s cold start on first request after a gap). The README notes
  this next to the live link rather than masking it with an external
  keep-warm pinger — an honest constraint reads better for a RegTech-adjacent
  portfolio piece than a disguised one.
