"""Detection engine entrypoint -- invoked as an Airflow task (see
airflow/dags/aml_pipeline_dag.py) and runnable standalone for local testing.

Loads the star schema, runs the deterministic rules and the Isolation Forest,
combines them into alerts, and writes the result to detection.alerts /
detection.alert_rule_triggers for the dbt marts/detection layer to pick up.
"""

import sys
import time

import pandas as pd

from detection.db import load_fact_transactions, reset_detection_schema, write_alerts, get_engine
from detection.features.engineer_features import build_features
from detection.model.train_isolation_forest import fit as fit_isolation_forest
from detection.model.score import score as score_isolation_forest
from detection.rules import structuring, velocity, high_risk_jurisdiction, circular_flow
from detection.scoring.combine_scores import build_alerts

RULES = [structuring, velocity, high_risk_jurisdiction, circular_flow]


def run() -> dict:
    start = time.time()

    transactions = load_fact_transactions()
    print(f"Loaded {len(transactions):,} transactions")

    rule_hits = []
    for rule_module in RULES:
        hits = rule_module.detect(transactions)
        print(f"  rule={rule_module.RULE_NAME}: {len(hits):,} transactions flagged")
        rule_hits.append(hits)
    rule_hits_df = pd.concat(rule_hits, ignore_index=True) if rule_hits else pd.DataFrame(
        columns=["transaction_key", "rule_name"]
    )

    features_df = build_features(transactions)
    print(f"Engineered features for {len(features_df):,} account-day observations")

    model, scaler = fit_isolation_forest(features_df)
    ml_scores_df = score_isolation_forest(features_df, model, scaler)

    alerts_df, rule_triggers_df = build_alerts(transactions, rule_hits_df, ml_scores_df)
    print(f"Generated {len(alerts_df):,} alerts")

    engine = get_engine()
    reset_detection_schema(engine)
    if not alerts_df.empty:
        write_alerts(alerts_df, rule_triggers_df, engine)

    elapsed = time.time() - start
    summary = {
        "rows_processed": len(transactions),
        "alerts_generated": len(alerts_df),
        "runtime_seconds": round(elapsed, 2),
    }
    print(f"Detection run complete: {summary}")
    return summary


if __name__ == "__main__":
    result = run()
    sys.exit(0 if result["rows_processed"] > 0 else 1)
