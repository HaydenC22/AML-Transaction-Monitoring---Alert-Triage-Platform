select
    alert_id,
    rule_name
from {{ source('detection', 'alert_rule_triggers') }}
