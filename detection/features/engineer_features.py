"""Per-account, per-simulated-day feature engineering for the Isolation Forest
model. Deliberately avoids raw balance columns (oldbalance/newbalance) as features
-- PaySim's fraud rows tend to zero out destination balances, which would let the
model learn that shortcut instead of genuine behavioral anomaly patterns. See
docs/adr/0003-hybrid-rules-plus-isolation-forest.md."""

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "txn_count",
    "mean_amount",
    "std_amount",
    "max_amount",
    "distinct_counterparty_count",
    "distinct_counterparty_country_count",
    "cash_out_ratio",
    "hour_entropy",
    "velocity_ratio",
    "in_degree",
]


def _entropy(hours: pd.Series) -> float:
    counts = hours.value_counts(normalize=True)
    return float(-(counts * np.log2(counts)).sum())


def build_features(transactions: pd.DataFrame) -> pd.DataFrame:
    outgoing = transactions.groupby(["origin_account_nk", "day_offset"])

    agg = outgoing.agg(
        txn_count=("transaction_key", "count"),
        mean_amount=("amount", "mean"),
        std_amount=("amount", "std"),
        max_amount=("amount", "max"),
        distinct_counterparty_count=("dest_account_nk", "nunique"),
        distinct_counterparty_country_count=("dest_country_code", "nunique"),
    ).reset_index()
    agg["std_amount"] = agg["std_amount"].fillna(0.0)

    cash_out_ratio = (
        transactions.assign(is_cash_out=(transactions["transaction_type"] == "CASH_OUT").astype(float))
        .groupby(["origin_account_nk", "day_offset"])["is_cash_out"]
        .mean()
        .reset_index(name="cash_out_ratio")
    )

    hour_entropy = (
        transactions.groupby(["origin_account_nk", "day_offset"])["hour_of_day"]
        .apply(_entropy)
        .reset_index(name="hour_entropy")
    )

    in_degree = (
        transactions.groupby(["dest_account_nk", "day_offset"])["origin_account_nk"]
        .nunique()
        .reset_index()
        .rename(columns={"dest_account_nk": "origin_account_nk", "origin_account_nk": "in_degree"})
    )

    features = agg.merge(cash_out_ratio, on=["origin_account_nk", "day_offset"])
    features = features.merge(hour_entropy, on=["origin_account_nk", "day_offset"])
    features = features.merge(in_degree, on=["origin_account_nk", "day_offset"], how="left")
    features["in_degree"] = features["in_degree"].fillna(0)

    daily_amount = agg[["origin_account_nk", "day_offset"]].copy()
    daily_amount["total_amount"] = (
        transactions.groupby(["origin_account_nk", "day_offset"])["amount"].sum().values
    )
    daily_amount = daily_amount.sort_values(["origin_account_nk", "day_offset"])
    daily_amount["baseline_mean"] = (
        daily_amount.groupby("origin_account_nk")["total_amount"]
        .transform(lambda s: s.shift(1).expanding().mean())
    )
    daily_amount["velocity_ratio"] = (
        daily_amount["total_amount"] / daily_amount["baseline_mean"].replace(0, np.nan)
    ).fillna(1.0).replace([np.inf, -np.inf], 10.0)

    features = features.merge(
        daily_amount[["origin_account_nk", "day_offset", "velocity_ratio"]],
        on=["origin_account_nk", "day_offset"],
    )

    return features
