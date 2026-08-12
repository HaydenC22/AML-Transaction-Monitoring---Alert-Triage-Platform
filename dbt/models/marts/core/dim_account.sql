{% set simulation_epoch = "2026-01-01" %}

select
    {{ dbt_utils.generate_surrogate_key(['account_nk']) }} as account_key,
    account_nk,
    (case when is_merchant then 'merchant' else 'customer' end) as account_role_type,
    is_merchant,
    (
        cast('{{ simulation_epoch }}' as date)
        - (('x' || substr(md5(account_nk || 'opened'), 1, 8))::bit(32)::bigint % 365)::int
    ) as opened_date
from {{ ref('int_accounts__geography_enriched') }}
