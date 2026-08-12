"""High-risk jurisdiction rule: flags any transaction where the origin or
destination account resolves to a synthetically high-risk (FATF monitored/
high-risk) jurisdiction -- see dbt/seeds/geography_risk_lookup.csv."""

import pandas as pd

RULE_NAME = "high_risk_jurisdiction"


def detect(transactions: pd.DataFrame) -> pd.DataFrame:
    hits = transactions[
        transactions["origin_is_high_risk"].fillna(False)
        | transactions["dest_is_high_risk"].fillna(False)
    ]
    if hits.empty:
        return pd.DataFrame(columns=["transaction_key", "rule_name"])

    result = hits[["transaction_key"]].drop_duplicates()
    result["rule_name"] = RULE_NAME
    return result
