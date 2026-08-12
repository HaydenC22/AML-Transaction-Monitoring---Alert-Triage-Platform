{#
  PaySim's `step` is a simulated hour offset (0-743 = 31 simulated days), not a real
  calendar date. Anchor the spine at a fixed epoch so date_key is stable and reproducible
  across pipeline runs, matching the deterministic-enrichment approach used for geography.
#}
{% set simulation_epoch = "2026-01-01" %}

with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('" ~ simulation_epoch ~ "' as date)",
        end_date="cast('" ~ simulation_epoch ~ "' as date) + interval '31 days'"
    ) }}
)

select
    cast(date_day as date) as full_date,
    (cast(date_day as date) - cast('{{ simulation_epoch }}' as date)) as simulated_day_offset
from spine
