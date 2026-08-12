with staged as (
    select * from {{ ref('stg_paysim__transactions') }}
),

deduped as (
    select
        *,
        row_number() over (
            partition by step, transaction_type, amount, origin_account_nk, dest_account_nk,
                         oldbalance_orig, newbalance_orig, oldbalance_dest, newbalance_dest
            order by source_row_id
        ) as dedup_rank
    from staged
)

select
    source_row_id,
    step,
    transaction_type,
    amount,
    origin_account_nk,
    oldbalance_orig,
    newbalance_orig,
    dest_account_nk,
    oldbalance_dest,
    newbalance_dest,
    is_fraud_label,
    is_paysim_flagged
from deduped
where dedup_rank = 1
