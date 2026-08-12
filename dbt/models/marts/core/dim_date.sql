select
    to_char(full_date, 'YYYYMMDD')::int as date_key,
    full_date,
    simulated_day_offset,
    extract(dow from full_date)::int as day_of_week,
    (extract(dow from full_date) in (0, 6)) as is_weekend,
    extract(month from full_date)::int as month,
    extract(quarter from full_date)::int as quarter,
    extract(year from full_date)::int as year
from {{ ref('int_date_spine') }}
