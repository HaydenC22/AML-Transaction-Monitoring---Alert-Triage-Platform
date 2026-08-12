{#
  Role-playing dimension over the same account entity as dim_account, used specifically
  for the *destination* side of a transaction. Modeled separately (Kimball role-playing
  pattern) because analysts query counterparty risk independently of account identity --
  e.g. "how risky is this destination" is a different question from "who owns this account".
#}
{% set simulation_epoch = "2026-01-01" %}

with dest_accounts as (
    select distinct dest_account_nk as account_nk
    from {{ ref('int_transactions__deduped') }}
),

enriched as (
    select a.*
    from {{ ref('int_accounts__geography_enriched') }} a
    inner join dest_accounts d using (account_nk)
),

txn_counts as (
    select account_nk, count(*) as lifetime_txn_count
    from (
        select origin_account_nk as account_nk from {{ ref('int_transactions__deduped') }}
        union all
        select dest_account_nk as account_nk from {{ ref('int_transactions__deduped') }}
    ) both_sides
    group by 1
)

select
    {{ dbt_utils.generate_surrogate_key(['e.account_nk']) }} as counterparty_key,
    e.account_nk as counterparty_nk,
    (case
        when e.is_merchant then 'merchant'
        when (('x' || substr(md5(e.account_nk || 'category'), 1, 8))::bit(32)::bigint % 100) < 5 then 'unknown'
        when (('x' || substr(md5(e.account_nk || 'category'), 1, 8))::bit(32)::bigint % 100) < 15 then 'exchange'
        else 'peer'
    end) as counterparty_category,
    ((('x' || substr(md5(e.account_nk || 'badactor'), 1, 8))::bit(32)::bigint % 1000) < 20) as is_high_risk_counterparty,
    coalesce(t.lifetime_txn_count, 0) as lifetime_txn_count,
    (
        cast('{{ simulation_epoch }}' as date) + (e.first_seen_step / 24)
    ) as first_seen_date
from enriched e
left join txn_counts t using (account_nk)
