{% set simulation_epoch = "2026-01-01" %}

with origin_accounts as (
    select distinct origin_account_nk as account_nk
    from {{ ref('int_transactions__deduped') }}
),

enriched as (
    select a.*
    from {{ ref('int_accounts__geography_enriched') }} a
    inner join origin_accounts o using (account_nk)
    where not a.is_merchant
)

select
    {{ dbt_utils.generate_surrogate_key(['account_nk']) }} as customer_key,
    account_nk as customer_nk,
    (case
        when (('x' || substr(md5(account_nk || 'type'), 1, 8))::bit(32)::bigint % 100) < 85
        then 'individual'
        else 'business'
    end) as customer_type,
    (case
        when (('x' || substr(md5(account_nk || 'risk'), 1, 8))::bit(32)::bigint % 100) < 70 then 'low'
        when (('x' || substr(md5(account_nk || 'risk'), 1, 8))::bit(32)::bigint % 100) < 95 then 'medium'
        else 'high'
    end) as risk_rating,
    (
        cast('{{ simulation_epoch }}' as date)
        - (('x' || substr(md5(account_nk || 'onboarding'), 1, 8))::bit(32)::bigint % 730)::int
    ) as onboarding_date,
    ((('x' || substr(md5(account_nk || 'active'), 1, 8))::bit(32)::bigint % 100) < 95) as is_active
from enriched
