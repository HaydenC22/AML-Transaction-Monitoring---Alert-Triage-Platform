with source as (
    select * from {{ source('raw', 'paysim_transactions') }}
)

select
    row_number() over (order by step, nameorig, namedest, amount) as source_row_id,
    step::int as step,
    upper(type) as transaction_type,
    amount::numeric(18, 2) as amount,
    nameorig as origin_account_nk,
    oldbalanceorg::numeric(18, 2) as oldbalance_orig,
    newbalanceorig::numeric(18, 2) as newbalance_orig,
    namedest as dest_account_nk,
    oldbalancedest::numeric(18, 2) as oldbalance_dest,
    newbalancedest::numeric(18, 2) as newbalance_dest,
    (isfraud = 1) as is_fraud_label,
    (isflaggedfraud = 1) as is_paysim_flagged
from source
