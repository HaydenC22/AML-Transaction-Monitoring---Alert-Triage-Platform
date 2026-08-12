"""Recomputes a recommended operating threshold using analyst dispositions as an
additional labeled signal alongside PaySim's synthetic ground truth, and writes a
*suggestion* to pipeline_state.threshold_recommendations -- never auto-applied.
A human still has to change CHOSEN_THRESHOLD in evaluate_thresholds.py and decide
to redeploy; this script only surfaces the recommendation in the Rules/Tuning
dashboard (GET /metrics/threshold-recommendation).

Run standalone for local testing, or on a low-frequency schedule (weekly, per the
project's build plan) since disposition volume accrues slowly relative to the
batch detection runs.
"""

import sys

import pandas as pd
from sqlalchemy import text

from detection.db import get_engine

TARGET_PRECISION = 0.15  # the precision level we'd like an operating threshold to clear
MIN_DISPOSITIONS_FOR_RECOMMENDATION = 5

QUERY = """
select
    a.composite_score::float as composite_score,
    a.is_fraud_label,
    d.outcome as disposition_outcome
from detection.alerts a
left join app.alert_dispositions d on d.alert_id = a.alert_id
"""

TOTAL_TXNS_QUERY = "select count(*) as c from raw_marts_core.fact_transactions"

UPSERT_SCHEMA = """
create schema if not exists pipeline_state;

create table if not exists pipeline_state.threshold_recommendations (
    recommendation_id serial primary key,
    recommended_threshold numeric(4, 2),
    dispositions_considered int not null,
    computed_at timestamp not null default now()
);
"""


def effective_label(row) -> bool:
    """Trust an analyst's disposition over the synthetic label when one exists --
    that's the real-world signal a production system would rely on."""
    if row["disposition_outcome"] is not None:
        return row["disposition_outcome"] == "true_positive"
    return bool(row["is_fraud_label"])


def recommend_threshold(df: pd.DataFrame, total_txns: int) -> float | None:
    thresholds = [round(0.05 + 0.05 * i, 2) for i in range(20)]
    best_meeting_target: float | None = None
    best_precision = -1.0
    best_threshold_overall = None

    for t in thresholds:
        flagged = df[df["composite_score"] >= t]
        if flagged.empty:
            continue
        precision = flagged["effective_label"].mean()
        if precision > best_precision:
            best_precision = precision
            best_threshold_overall = t
        if precision >= TARGET_PRECISION and best_meeting_target is None:
            best_meeting_target = t

    return best_meeting_target or best_threshold_overall


def main() -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(QUERY), conn)
        total_txns = pd.read_sql(text(TOTAL_TXNS_QUERY), conn)["c"].iloc[0]

    dispositions_considered = df["disposition_outcome"].notna().sum()
    if dispositions_considered < MIN_DISPOSITIONS_FOR_RECOMMENDATION:
        print(
            f"Only {dispositions_considered} dispositions logged "
            f"(need {MIN_DISPOSITIONS_FOR_RECOMMENDATION}) -- skipping recommendation."
        )
        return {"dispositions_considered": int(dispositions_considered), "recommended_threshold": None}

    df["effective_label"] = df.apply(effective_label, axis=1)
    recommended = recommend_threshold(df, total_txns)

    with engine.begin() as conn:
        conn.execute(text(UPSERT_SCHEMA))
        conn.execute(
            text(
                """
                insert into pipeline_state.threshold_recommendations
                    (recommended_threshold, dispositions_considered)
                values (:recommended_threshold, :dispositions_considered)
                """
            ),
            {
                "recommended_threshold": recommended,
                "dispositions_considered": int(dispositions_considered),
            },
        )

    print(f"Recommended threshold: {recommended} (from {dispositions_considered} dispositions)")
    return {"dispositions_considered": int(dispositions_considered), "recommended_threshold": recommended}


if __name__ == "__main__":
    result = main()
    sys.exit(0)
