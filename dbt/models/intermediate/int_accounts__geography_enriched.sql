{#
  PaySim has no jurisdiction field. Each account is deterministically assigned a
  synthetic country by hashing its natural key into a bucket, then mapping that bucket
  against the geography seed's weighted cumulative ranges -- reproducible across runs
  without being stored state. See dbt/seeds/geography_risk_lookup.csv and the README's
  synthetic-enrichment disclosure.
#}

with geography_seed as (
    select
        *,
        sum(assignment_weight) over () as total_weight,
        sum(assignment_weight) over (
            order by country_code
            rows between unbounded preceding and current row
        ) as cumulative_weight
    from {{ ref('geography_risk_lookup') }}
),

geography_ranges as (
    select
        country_code,
        country_name,
        region,
        fatf_risk_category,
        is_high_risk,
        is_sanctioned_synthetic,
        (cumulative_weight - assignment_weight) as range_start,
        cumulative_weight as range_end,
        total_weight
    from geography_seed
),

account_buckets as (
    select
        account_nk,
        is_merchant,
        first_seen_step,
        (('x' || substr(md5(account_nk), 1, 8))::bit(32)::bigint % (select max(total_weight) from geography_ranges)) as bucket
    from {{ ref('int_accounts__unique') }}
)

select
    b.account_nk,
    b.is_merchant,
    b.first_seen_step,
    g.country_code,
    g.country_name,
    g.region,
    g.fatf_risk_category,
    g.is_high_risk,
    g.is_sanctioned_synthetic
from account_buckets b
join geography_ranges g
    on b.bucket >= g.range_start and b.bucket < g.range_end
