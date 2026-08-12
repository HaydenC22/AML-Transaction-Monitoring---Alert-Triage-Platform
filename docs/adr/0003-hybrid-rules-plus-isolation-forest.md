# ADR-0003: Hybrid deterministic rules + Isolation Forest instead of a supervised classifier

## Status
Accepted

## Context
PaySim (and this project's schema-compatible synthetic generator) provides a
ground-truth `isFraud` label, which makes a supervised classifier (logistic
regression, gradient boosting, etc.) technically available. The alternative is
a hybrid design: deterministic rules (structuring, velocity spikes, high-risk
jurisdiction, circular flow) plus an unsupervised Isolation Forest, combined
into one composite score.

## Decision
Build the hybrid engine. Each rule contributes a fixed weight to a composite
score; the Isolation Forest's anomaly score (rank-normalized to [0, 1]) is one
more weighted signal alongside them — never a black-box override.

## Consequences
- **Explainability.** An analyst dispositioning an alert needs to write a
  rationale. "The model said 0.87" is not a rationale; "structuring +
  velocity spike, composite 0.90" is. `fct_alert_rule_triggers` gives every
  rule-driven alert a documented reason; ML-only alerts are explicitly labeled
  as such in the case detail view rather than implied to have a rule behind them.
- **Generalization beyond the label set.** PaySim's fraud labels cover exactly
  the typologies the simulator encodes. A supervised model trained on those
  labels would (over)fit to that narrow pattern set. The Isolation Forest
  scores behavioral anomaly directly from engineered features, independent of
  whether that specific pattern was ever labeled as fraud — closer to how a
  production system has to handle typologies it hasn't seen yet.
- **Lower theoretical ceiling.** A well-labeled supervised model would likely
  outperform this hybrid on this specific synthetic dataset's precision/recall,
  precisely because the labels and the test data come from the same narrow
  generative process. That's a real cost, accepted deliberately — optimizing
  for a benchmark that only exists because of the synthetic label set isn't
  the goal here.
- **Concrete result on this dataset:** the hybrid engine reaches 0.9% precision
  unfiltered, climbing to 31%+ precision at the `critical` severity tier
  (composite score ≥ 0.80) — see `docs/metrics/latest_evaluation_report.md`
  for the full threshold sweep. That tiering, not a single global threshold, is
  the actual point of the design: it's what makes severity-based triage
  (`low`/`medium`/`high`/`critical`) a meaningful axis instead of decoration.
