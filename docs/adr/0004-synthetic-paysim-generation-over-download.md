# ADR-0004: Generate PaySim-schema synthetic data instead of downloading the real Kaggle dataset

## Status
Accepted

## Context
[PaySim](https://www.kaggle.com/datasets/ealaxi/paysim1) is the standard
synthetic mobile-money dataset for this kind of project — well-documented,
schema-simple, and it ships a genuine `isFraud` label. It's also
Kaggle-hosted, which means fetching it programmatically requires an
authenticated Kaggle API token. That conflicts directly with this project's
"`docker compose up`, no signup" requirement: a reviewer without a Kaggle
account, or one whose token setup fails, would hit a broken first-run
experience — the single artifact a 90-second repo review actually judges.

## Decision
[`scripts/generate_paysim_sample.py`](../../scripts/generate_paysim_sample.py)
generates a seeded, fully reproducible dataset matching PaySim's exact column
schema (`step`, `type`, `amount`, `nameOrig`, `oldbalanceOrg`,
`newbalanceOrig`, `nameDest`, `oldbalanceDest`, `newbalanceDest`, `isFraud`,
`isFlaggedFraud`) and its documented quirks (merchant destination balances are
never tracked; fraud transactions tend to zero out destination balances — the
label-leakage pattern that motivates ADR-0003's feature engineering choices).
`data/raw/` remains a documented fallback for anyone who does want to drop in
the real Kaggle file instead.

## Consequences
- Zero licensing/redistribution question, since nothing Kaggle-sourced is
  committed to the repo — a strictly cleaner position than redistributing a
  stratified sample would have been.
- Full control over typology coverage. The real PaySim dataset's fraud rows
  are essentially one pattern (TRANSFER-then-CASH_OUT draining). Two of this
  project's four detection rules — `structuring` and `circular_flow` — would
  have had **zero true positives to ever detect**, permanently, on the real
  data. Discovered exactly this way during Week 2 testing (both rules fired 0
  times), which is why the generator explicitly injects structuring episodes
  (sub-threshold transfer clusters) and circular-flow episodes (short transfer
  cycles) alongside the original drain pattern.
- Cost: this is a simulation of PaySim's *schema and known characteristics*,
  not a redistribution of its actual generative model — the amount
  distributions, account population, and fraud rate are approximations, not
  a byte-for-byte statistical match. Acceptable for a portfolio MVP; would not
  be acceptable as a substitute for benchmarking against published PaySim
  results in a research context.
