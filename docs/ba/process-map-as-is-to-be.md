# Alert Triage Process Map: As-Is → To-Be

## As-Is: rules-only, manual triage

Before the hybrid engine and structured triage queue, the process an AML
operations team runs looks like this:

```mermaid
flowchart LR
    subgraph System[System]
        A1[Rules engine flags<br/>transactions] --> A2[Alerts dumped to<br/>a shared spreadsheet]
    end
    subgraph Analyst[Analyst]
        A2 --> A3[Analyst scans spreadsheet<br/>top-to-bottom, no priority order]
        A3 --> A4[Manually investigates<br/>each alert]
        A4 --> A5[Marks TP/FP in a<br/>spreadsheet column]
    end
    subgraph Compliance[Compliance Lead]
        A5 --> A6[No structured visibility into<br/>FP rate or backlog]
        A6 --> A7[Rule thresholds tuned<br/>ad hoc, rarely, on gut feel]
    end
```

**Pain points:**
- No severity ordering — analysts work whatever's at the top of the sheet, not
  whatever's riskiest.
- Dispositions live in a spreadsheet column, disconnected from the alert's
  original context (which rule fired, the transaction amount, account history).
- No feedback loop: rule thresholds are tuned from memory and intuition, not
  from actual disposition outcomes.
- No visibility into the false-positive rate or analyst throughput — the
  operational pain (alert fatigue) is invisible until someone complains.

## To-Be: hybrid scoring, prioritized queue, closed feedback loop

```mermaid
flowchart LR
    subgraph System[System]
        B1[Hybrid engine: rules +<br/>Isolation Forest] --> B2[Composite score →<br/>severity bucket]
        B2 --> B3[fct_alerts +<br/>rule-trigger explanations]
    end
    subgraph Analyst[Analyst]
        B3 --> B4[Queue sorted by<br/>severity/score]
        B4 --> B5[Case detail: rules,<br/>account history, ML score]
        B5 --> B6[Disposition + rationale<br/>captured per alert]
    end
    subgraph Compliance[Compliance Lead]
        B6 --> B7[Overview dashboard: FP rate,<br/>volume, throughput trends]
        B6 --> B8[Weekly recompute: recommended<br/>threshold from real dispositions]
        B8 --> B9[Human reviews & decides<br/>whether to retune]
        B9 -.-> B1
    end
```

**What changed:**
- **Prioritization**: alerts are severity-bucketed from a composite score, so
  `critical` (31%+ precision) gets worked before `low` (0% precision in the
  current evaluation — see `docs/metrics/latest_evaluation_report.md`).
- **Context at the point of decision**: case detail shows exactly which
  rule(s) fired and why, plus account transaction history, so a disposition
  rationale is grounded in specifics rather than reconstructed from memory.
- **Structured, auditable dispositions**: `app.alert_dispositions` — one
  disposition per alert, immutable once submitted, always paired with a
  rationale.
- **Closed feedback loop**: `recompute_from_dispositions.py` turns analyst
  decisions back into a *recommended* threshold — surfaced to a human on the
  Rules & Tuning page, never auto-applied (see ADR-0003).
- **Visibility for compliance leadership**: the Overview dashboard makes the
  FP rate, alert volume trend, and analyst throughput a first-class, always-on
  view instead of something inferred from a spreadsheet on request.
