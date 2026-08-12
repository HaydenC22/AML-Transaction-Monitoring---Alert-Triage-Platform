"""Shared warehouse access for the detection engine: loads the star schema into a
flat pandas DataFrame (natural keys, not surrogate keys, since rules reason about
account identities and geography directly) and manages the `detection` schema that
holds the engine's own output (upstream of the dbt marts/detection layer)."""

import os

import pandas as pd
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get(
    "WAREHOUSE_DATABASE_URL",
    "postgresql://aml:aml@pg-warehouse:5432/aml_warehouse",
)

FACT_QUERY = """
select
    f.transaction_key,
    d.simulated_day_offset as day_offset,
    f.hour_of_day,
    f.transaction_type,
    f.amount::float as amount,
    f.is_fraud_label,
    oa.account_nk as origin_account_nk,
    da.account_nk as dest_account_nk,
    og.country_code as origin_country_code,
    og.is_high_risk as origin_is_high_risk,
    dg.country_code as dest_country_code,
    dg.is_high_risk as dest_is_high_risk
from raw_marts_core.fact_transactions f
join raw_marts_core.dim_date d on d.date_key = f.date_key
join raw_marts_core.dim_account oa on oa.account_key = f.origin_account_key
join raw_marts_core.dim_account da on da.account_key = f.dest_account_key
left join raw_marts_core.dim_geography og on og.geography_key = f.origin_geography_key
left join raw_marts_core.dim_geography dg on dg.geography_key = f.dest_geography_key
order by d.simulated_day_offset, f.hour_of_day
"""

CREATE_DETECTION_SCHEMA = """
create schema if not exists detection;

drop table if exists detection.alert_rule_triggers;
drop table if exists detection.alerts;

create table detection.alerts (
    alert_id serial primary key,
    transaction_key varchar(64) not null,
    origin_account_nk varchar(32) not null,
    day_offset int not null,
    ml_anomaly_score numeric(6, 4) not null,
    composite_score numeric(6, 4) not null,
    severity varchar(16) not null,
    is_fraud_label boolean not null,
    created_at timestamp not null default now()
);

create table detection.alert_rule_triggers (
    alert_id int not null references detection.alerts(alert_id),
    rule_name varchar(64) not null
);

create index on detection.alerts (transaction_key);
create index on detection.alerts (severity);
"""


def get_engine():
    return create_engine(DATABASE_URL)


def load_fact_transactions() -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(FACT_QUERY), conn)
    return df


def reset_detection_schema(engine=None) -> None:
    engine = engine or get_engine()
    with engine.begin() as conn:
        conn.execute(text(CREATE_DETECTION_SCHEMA))


def write_alerts(alerts_df: pd.DataFrame, rule_triggers_df: pd.DataFrame, engine=None) -> None:
    engine = engine or get_engine()
    alerts_df.to_sql("alerts", engine, schema="detection", if_exists="append", index=False)

    with engine.connect() as conn:
        key_map = pd.read_sql(
            text("select alert_id, transaction_key from detection.alerts"), conn
        )
    merged = rule_triggers_df.merge(key_map, on="transaction_key", how="inner")
    merged[["alert_id", "rule_name"]].to_sql(
        "alert_rule_triggers", engine, schema="detection", if_exists="append", index=False
    )
