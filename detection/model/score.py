"""Applies a fitted Isolation Forest to produce a normalized [0, 1] anomaly score
per account-day, where 1.0 is the most anomalous. Raw sklearn decision_function
scores aren't on a stable, interpretable scale, so scores are rank-normalized
within the batch instead."""

import pandas as pd

from detection.features.engineer_features import FEATURE_COLUMNS


def score(features_df: pd.DataFrame, model, scaler) -> pd.DataFrame:
    X = features_df[FEATURE_COLUMNS].to_numpy()
    X_scaled = scaler.transform(X)

    raw_scores = -model.decision_function(X_scaled)  # higher = more anomalous
    result = features_df[["origin_account_nk", "day_offset"]].copy()
    result["ml_anomaly_score"] = pd.Series(raw_scores).rank(pct=True).to_numpy()
    return result
