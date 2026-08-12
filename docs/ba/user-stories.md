# User Stories (INVEST format)

Five stories tied directly to the shipped screens and API — not generic
placeholders. Each is Independent, Negotiable, Valuable, Estimable, Small, and
Testable against the actual system in this repo.

---

### 1. Severity-prioritized queue

**As an** AML analyst,
**I want** the alert queue sorted by severity by default,
**so that** I triage the highest-risk cases first instead of working
top-to-bottom through an unordered list.

**Acceptance criteria:**
- `GET /alerts` default-sorts by `composite_score` descending.
- Each row shows a severity stamp (`low`/`medium`/`high`/`critical`).
- Selecting a severity filter persists across pagination (page resets to 1,
  filter stays applied until changed).

---

### 2. Auditable disposition with rationale

**As an** AML analyst,
**I want** to disposition an alert with a required rationale,
**so that** my decision is auditable and defensible in a compliance review.

**Acceptance criteria:**
- `POST /alerts/{id}/disposition` requires `outcome` (`true_positive` or
  `false_positive`) and a non-empty `rationale_notes`.
- A disposition is timestamped (`dispositioned_at`) and immutable — a second
  disposition attempt on the same alert returns `409 Conflict`.
- Once dispositioned, the case detail view replaces the form with the
  submitted outcome, rationale, analyst, and timestamp — never silently editable.

---

### 3. False-positive rate visibility for compliance leads

**As a** compliance lead,
**I want** to see the false-positive rate trend and severity breakdown,
**so that** I can judge whether current thresholds are generating too much
noise without asking an analyst to pull a report.

**Acceptance criteria:**
- The Overview dashboard shows alert volume by day, severity breakdown, and
  FP-rate trend, computed live from `GET /metrics/overview`.
- Precision-by-severity is visible (e.g. `critical` tier precision vs. overall
  precision), so the value of severity-based triage is demonstrated with
  numbers, not asserted.

---

### 4. Recommended threshold from real feedback

**As a** compliance lead,
**I want** a recommended operating threshold computed from recent analyst
dispositions,
**so that** tuning is grounded in real outcomes rather than manual guesswork —
without losing human sign-off on the actual change.

**Acceptance criteria:**
- `GET /metrics/threshold-recommendation` returns a recommendation only once
  at least 5 dispositions have been logged (below that, it reports "not yet
  available" rather than a noisy estimate from 1-2 data points).
- The Rules & Tuning page shows current vs. recommended threshold side by
  side, with the disposition count backing the recommendation.
- The recommendation is never auto-applied — changing `CHOSEN_THRESHOLD`
  requires a human editing the detection engine's config and redeploying (ADR-0003).

---

### 5. Account context without leaving the case

**As an** AML analyst,
**I want** to see an account's recent transaction activity on the case detail
page,
**so that** I can judge whether a flagged transaction fits a pattern without
switching tools or losing my place.

**Acceptance criteria:**
- Case detail shows a transaction-count-per-day chart for the alert's origin
  account (`GET /metrics/cases/{id}/timeline`).
- The chart renders even when history is sparse (a single active day still
  produces a valid, non-broken chart).
- No separate navigation or tool switch is required — the history is embedded
  in the same case detail view as the disposition form.
