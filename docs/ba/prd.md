# PRD: AML Transaction Monitoring & Alert Triage Platform

## Problem

AML transaction monitoring systems are notorious for generating far more
alerts than analysts can review — the industry-standard pain point is a
false-positive rate often cited north of 90%. Singapore's DTSP licensing
regime (in force since 30 June 2025, requiring a locally based compliance
officer) has driven real hiring demand for people who can build and operate
this exact kind of system. A rules-only engine with no prioritization or
feedback loop makes the problem worse, not better: everything looks equally
urgent, and tuning happens on gut feel instead of evidence.

## Target users

- **AML analyst** — works the alert queue daily, needs to triage fast and
  document defensible decisions.
- **Compliance lead** — owns the overall control's effectiveness, needs
  visibility into FP rate and throughput, and signs off on threshold changes.

## Scope

**In scope:**
- Hybrid rules + ML detection engine (structuring, velocity, jurisdiction,
  circular-flow rules + Isolation Forest anomaly scoring).
- Severity-prioritized alert queue with filtering.
- Case detail with rule explanations, account history, disposition capture.
- Dashboard: alert volume, FP-rate trend, severity breakdown, pipeline health.
- Disposition-driven threshold recommendation (human-approved, never auto-applied).
- Full data pipeline: ingestion → dbt star schema → Great Expectations
  validation → detection → evaluation, orchestrated by Airflow.

**Out of scope (explicitly):**
- Real SAR (Suspicious Activity Report) filing or regulator submission.
- Real sanctions/watchlist screening (the "high-risk jurisdiction" rule uses a
  synthetic geography seed, not an actual sanctions list).
- Multi-tenant access control / analyst authentication (single shared view for
  this MVP).
- Real-time/streaming detection (this is a batch pipeline, full-refresh per ADR-0002).

## Success metrics

- **Precision at the `critical` severity tier** — currently 31%+ against an
  overall unfiltered precision of 0.9%, demonstrating that severity tiering
  concentrates true positives where analysts look first (see
  `docs/metrics/latest_evaluation_report.md` for the full curve).
- **False-positive rate at the chosen operating threshold** — currently 1.5%
  of all transactions at threshold 0.60, vs. 9.5% unfiltered.
- **Recall retained at the chosen threshold** — 19.7%, the deliberate
  trade-off point against the precision/FP-rate gain above.
- **Pipeline data-quality pass rate** — Great Expectations SLA is ≥99% of
  expectations passing at both the raw and marts layers; the pipeline fails
  fast if breached.
- **Rows processed / pipeline runtime** — ~200K rows in under 15 seconds for
  the full dbt build; detection scoring in under a minute — tracked per run in
  `pipeline_state.pipeline_runs`.

## Risks & assumptions

- All data is synthetic (see `data/sample/DATA_DICTIONARY.md` and ADR-0004).
  Detection performance numbers are demonstrative of the *approach*, not a
  claim about real-world AML detection rates.
- The geography risk seed is a synthetic 18-country lookup, not a real FATF or
  sanctions list — explicitly disclosed, not a compliance claim.
- Alert identity is not stable across full pipeline re-runs (ADR-0002) — a
  known limitation for a full-refresh MVP, with a documented fix path.
