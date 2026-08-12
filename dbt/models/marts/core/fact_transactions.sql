with txns as (
    select * from {{ ref('int_transactions__deduped') }}
),

origin_geo as (
    select account_nk, country_code from {{ ref('int_accounts__geography_enriched') }}
),

dest_geo as (
    select account_nk, country_code from {{ ref('int_accounts__geography_enriched') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['t.source_row_id']) }} as transaction_key,
    d.date_key,
    mod(t.step, 24) as hour_of_day,
    oa.account_key as origin_account_key,
    dc.customer_key as origin_customer_key,
    da.account_key as dest_account_key,
    cp.counterparty_key as counterparty_key,
    og.geography_key as origin_geography_key,
    dg.geography_key as dest_geography_key,
    t.transaction_type,
    t.amount,
    t.oldbalance_orig,
    t.newbalance_orig,
    t.oldbalance_dest,
    t.newbalance_dest,
    t.is_fraud_label,
    t.is_paysim_flagged,
    now() as loaded_at
from txns t
inner join {{ ref('dim_date') }} d
    on d.simulated_day_offset = (t.step / 24)
left join {{ ref('dim_account') }} oa
    on oa.account_nk = t.origin_account_nk
left join {{ ref('dim_customer') }} dc
    on dc.customer_nk = t.origin_account_nk
left join {{ ref('dim_account') }} da
    on da.account_nk = t.dest_account_nk
left join {{ ref('dim_counterparty') }} cp
    on cp.counterparty_nk = t.dest_account_nk
left join origin_geo og_acct
    on og_acct.account_nk = t.origin_account_nk
left join {{ ref('dim_geography') }} og
    on og.country_code = og_acct.country_code
left join dest_geo dg_acct
    on dg_acct.account_nk = t.dest_account_nk
left join {{ ref('dim_geography') }} dg
    on dg.country_code = dg_acct.country_code
