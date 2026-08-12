select
    {{ dbt_utils.generate_surrogate_key(['country_code']) }} as geography_key,
    country_code,
    country_name,
    region,
    fatf_risk_category,
    is_high_risk,
    is_sanctioned_synthetic
from {{ ref('geography_risk_lookup') }}
