"""Combines deterministic rule triggers and the Isolation Forest anomaly score into
a single explainable alert per transaction. Each rule contributes a fixed weight
rather than the ML score silently overriding everything -- analysts need to see
*why* an alert fired for their disposition rationale, not just a black-box number.
See docs/adr/0003-hybrid-rules-plus-isolation-forest.md.

A transaction becomes an alert if either (a) at least one rule fired for it, or
(b) its account-day ML anomaly score is in the top ML_INCLUSION_PERCENTILE (an
ML-only alert with no rule explanation, which is a legitimate and expected outcome
of an unsupervised model -- flagged as such via an empty rule_flags list).
"""

import pandas as pd

RULE_WEIGHTS = {
    "structuring": 0.35,
    "velocity_spike": 0.25,
    "high_risk_jurisdiction": 0.15,
    "circular_flow": 0.40,
}
ML_WEIGHT = 0.5
ML_INCLUSION_PERCENTILE = 0.98

SEVERITY_THRESHOLDS = [
    (0.80, "critical"),
    (0.60, "high"),
    (0.35, "medium"),
]
DEFAULT_SEVERITY = "low"


def _severity_for(score: float) -> str:
    for threshold, label in SEVERITY_THRESHOLDS:
        if score >= threshold:
            return label
    return DEFAULT_SEVERITY


def build_alerts(
    transactions: pd.DataFrame,
    rule_hits: pd.DataFrame,
    ml_scores: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    txns = transactions.merge(
        ml_scores, on=["origin_account_nk", "day_offset"], how="left"
    )
    txns["ml_anomaly_score"] = txns["ml_anomaly_score"].fillna(0.0)

    rule_weight_by_txn = (
        rule_hits.assign(weight=rule_hits["rule_name"].map(RULE_WEIGHTS))
        .groupby("transaction_key")["weight"]
        .sum()
        .rename("rule_weight_sum")
    )

    candidates = set(rule_hits["transaction_key"].unique())
    ml_only = txns[txns["ml_anomaly_score"] >= ML_INCLUSION_PERCENTILE]["transaction_key"]
    candidates.update(ml_only.tolist())

    if not candidates:
        empty_alerts = pd.DataFrame(
            columns=[
                "transaction_key", "origin_account_nk", "day_offset",
                "ml_anomaly_score", "composite_score", "severity", "is_fraud_label",
            ]
        )
        empty_triggers = pd.DataFrame(columns=["transaction_key", "rule_name"])
        return empty_alerts, empty_triggers

    alerts = txns[txns["transaction_key"].isin(candidates)].copy()
    alerts = alerts.merge(rule_weight_by_txn, on="transaction_key", how="left")
    alerts["rule_weight_sum"] = alerts["rule_weight_sum"].fillna(0.0)

    alerts["composite_score"] = (
        alerts["rule_weight_sum"] + ML_WEIGHT * alerts["ml_anomaly_score"]
    ).clip(upper=1.0)
    alerts["severity"] = alerts["composite_score"].apply(_severity_for)

    alerts = alerts[
        [
            "transaction_key", "origin_account_nk", "day_offset",
            "ml_anomaly_score", "composite_score", "severity", "is_fraud_label",
        ]
    ].drop_duplicates(subset=["transaction_key"])

    rule_triggers = rule_hits[rule_hits["transaction_key"].isin(candidates)][
        ["transaction_key", "rule_name"]
    ].drop_duplicates()

    return alerts, rule_triggers
