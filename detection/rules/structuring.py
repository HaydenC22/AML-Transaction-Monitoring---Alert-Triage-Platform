"""Structuring/smurfing rule: flags an origin account's transactions on a given
simulated day when several of them cluster just under a round reporting threshold
and together add up to a materially larger sum -- the classic "smurfing" pattern of
splitting a large transfer into sub-threshold pieces."""

import pandas as pd

RULE_NAME = "structuring"
BAND_LOW = 9_000
BAND_HIGH = 9_999
MIN_TXNS_IN_BAND = 3
MIN_AGGREGATE_AMOUNT = 25_000


def detect(transactions: pd.DataFrame) -> pd.DataFrame:
    in_band = transactions[
        (transactions["amount"] >= BAND_LOW) & (transactions["amount"] <= BAND_HIGH)
    ]
    if in_band.empty:
        return _empty_result()

    grouped = in_band.groupby(["origin_account_nk", "day_offset"]).agg(
        txn_count=("transaction_key", "count"),
        aggregate_amount=("amount", "sum"),
    )
    flagged_groups = grouped[
        (grouped["txn_count"] >= MIN_TXNS_IN_BAND)
        & (grouped["aggregate_amount"] >= MIN_AGGREGATE_AMOUNT)
    ]
    if flagged_groups.empty:
        return _empty_result()

    flagged_keys = flagged_groups.index
    hits = in_band.set_index(["origin_account_nk", "day_offset"]).loc[flagged_keys]
    result = hits.reset_index()[["transaction_key"]].drop_duplicates()
    result["rule_name"] = RULE_NAME
    return result


def _empty_result() -> pd.DataFrame:
    return pd.DataFrame(columns=["transaction_key", "rule_name"])
