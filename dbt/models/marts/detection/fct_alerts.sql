with alerts as (
    select * from {{ source('detection', 'alerts') }}
),

txns as (
    select * from {{ ref('fact_transactions') }}
)

select
    a.alert_id,
    a.transaction_key,
    t.transaction_type,
    t.amount,
    t.date_key,
    a.origin_account_nk,
    t.origin_account_key,
    t.dest_account_key,
    t.origin_geography_key,
    t.dest_geography_key,
    a.day_offset,
    a.ml_anomaly_score,
    a.composite_score,
    a.severity,
    a.is_fraud_label,
    a.created_at
from alerts a
left join txns t on t.transaction_key = a.transaction_key
