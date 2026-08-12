with origins as (
    select distinct origin_account_nk as account_nk
    from {{ ref('stg_paysim__transactions') }}
),

dests as (
    select distinct dest_account_nk as account_nk
    from {{ ref('stg_paysim__transactions') }}
),

all_accounts as (
    select account_nk from origins
    union
    select account_nk from dests
),

first_seen as (
    select
        account_nk,
        min(first_seen_step) as first_seen_step
    from (
        select origin_account_nk as account_nk, min(step) as first_seen_step
        from {{ ref('stg_paysim__transactions') }}
        group by 1
        union all
        select dest_account_nk as account_nk, min(step) as first_seen_step
        from {{ ref('stg_paysim__transactions') }}
        group by 1
    ) seen
    group by 1
)

select
    a.account_nk,
    (left(a.account_nk, 1) = 'M') as is_merchant,
    f.first_seen_step
from all_accounts a
left join first_seen f using (account_nk)
