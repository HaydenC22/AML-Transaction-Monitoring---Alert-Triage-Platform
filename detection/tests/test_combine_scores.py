import pandas as pd

from detection.scoring.combine_scores import ML_INCLUSION_PERCENTILE, RULE_WEIGHTS, build_alerts


def _txn(key, orig, day, is_fraud=False):
    return {
        "transaction_key": key,
        "origin_account_nk": orig,
        "day_offset": day,
        "is_fraud_label": is_fraud,
    }


def test_rule_only_alert_gets_weighted_composite_score():
    txns = pd.DataFrame([_txn("t1", "C1", 0)])
    rule_hits = pd.DataFrame([{"transaction_key": "t1", "rule_name": "structuring"}])
    ml_scores = pd.DataFrame([{"origin_account_nk": "C1", "day_offset": 0, "ml_anomaly_score": 0.0}])

    alerts, triggers = build_alerts(txns, rule_hits, ml_scores)

    assert len(alerts) == 1
    assert alerts.iloc[0]["composite_score"] == RULE_WEIGHTS["structuring"]
    assert set(triggers["rule_name"]) == {"structuring"}


def test_multiple_rules_stack_additively_and_cap_at_one():
    txns = pd.DataFrame([_txn("t1", "C1", 0)])
    rule_hits = pd.DataFrame(
        [
            {"transaction_key": "t1", "rule_name": "structuring"},
            {"transaction_key": "t1", "rule_name": "velocity_spike"},
            {"transaction_key": "t1", "rule_name": "circular_flow"},
        ]
    )
    ml_scores = pd.DataFrame([{"origin_account_nk": "C1", "day_offset": 0, "ml_anomaly_score": 1.0}])

    alerts, _ = build_alerts(txns, rule_hits, ml_scores)
    assert alerts.iloc[0]["composite_score"] == 1.0  # clipped, since raw sum exceeds 1.0


def test_ml_only_alert_has_no_rule_triggers():
    txns = pd.DataFrame([_txn("t1", "C1", 0), _txn("t2", "C2", 0)])
    rule_hits = pd.DataFrame(columns=["transaction_key", "rule_name"])
    ml_scores = pd.DataFrame(
        [
            {"origin_account_nk": "C1", "day_offset": 0, "ml_anomaly_score": ML_INCLUSION_PERCENTILE},
            {"origin_account_nk": "C2", "day_offset": 0, "ml_anomaly_score": 0.1},
        ]
    )

    alerts, triggers = build_alerts(txns, rule_hits, ml_scores)
    assert set(alerts["transaction_key"]) == {"t1"}
    assert triggers.empty


def test_transaction_below_all_thresholds_is_not_an_alert():
    txns = pd.DataFrame([_txn("t1", "C1", 0)])
    rule_hits = pd.DataFrame(columns=["transaction_key", "rule_name"])
    ml_scores = pd.DataFrame([{"origin_account_nk": "C1", "day_offset": 0, "ml_anomaly_score": 0.2}])

    alerts, _ = build_alerts(txns, rule_hits, ml_scores)
    assert alerts.empty


def test_no_candidates_returns_empty_frames_with_expected_columns():
    txns = pd.DataFrame([_txn("t1", "C1", 0)])
    rule_hits = pd.DataFrame(columns=["transaction_key", "rule_name"])
    ml_scores = pd.DataFrame([{"origin_account_nk": "C1", "day_offset": 0, "ml_anomaly_score": 0.0}])

    alerts, triggers = build_alerts(txns, rule_hits, ml_scores)
    assert list(alerts.columns) == [
        "transaction_key", "origin_account_nk", "day_offset",
        "ml_anomaly_score", "composite_score", "severity", "is_fraud_label",
    ]
    assert list(triggers.columns) == ["transaction_key", "rule_name"]
