"""Fits an Isolation Forest over the engineered account-day feature vectors.
Retrained from scratch on each pipeline run against that run's full transaction
history -- reasonable for this MVP's batch-scoring cadence; model persistence/
versioning across runs is a documented "what's next" item, not built here."""

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from detection.features.engineer_features import FEATURE_COLUMNS

RANDOM_STATE = 42
CONTAMINATION = 0.03


def fit(features_df):
    X = features_df[FEATURE_COLUMNS].to_numpy()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_scaled)
    return model, scaler
