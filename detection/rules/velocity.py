"""Velocity-spike rule: flags an origin account's transactions on a day where its
total outgoing amount is a large multiple of its own trailing baseline -- a sudden
burst of activity relative to the account's established behavior."""

import pandas as pd

RULE_NAME = "velocity_spike"
SPIKE_MULTIPLIER = 5.0
MIN_BASELINE_DAYS = 5  # accounts transact rarely in this dataset; require real history
MIN_CURRENT_DAY_AMOUNT = 8_000  # avoid flagging trivial spikes on near-zero baselines


def detect(transactions: pd.DataFrame) -> pd.DataFrame:
    daily = (
        transactions.groupby(["origin_account_nk", "day_offset"])["amount"]
        .sum()
        .reset_index()
        .sort_values(["origin_account_nk", "day_offset"])
    )

    daily["baseline_mean"] = (
        daily.groupby("origin_account_nk")["amount"]
        .transform(lambda s: s.shift(1).expanding().mean())
    )
    daily["baseline_days"] = (
        daily.groupby("origin_account_nk").cumcount()
    )

    spikes = daily[
        (daily["baseline_days"] >= MIN_BASELINE_DAYS)
        & (daily["amount"] >= MIN_CURRENT_DAY_AMOUNT)
        & (daily["amount"] > daily["baseline_mean"] * SPIKE_MULTIPLIER)
    ]
    if spikes.empty:
        return pd.DataFrame(columns=["transaction_key", "rule_name"])

    result = transactions.merge(
        spikes[["origin_account_nk", "day_offset"]],
        on=["origin_account_nk", "day_offset"],
        how="inner",
    )[["transaction_key"]].drop_duplicates()
    result["rule_name"] = RULE_NAME
    return result
