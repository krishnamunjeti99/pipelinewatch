-- A valid percentage is between 0 and 100. Any row outside that range
-- indicates a bug in the mart logic. This query should return zero rows.
select
    service,
    event_date,
    event_hour,
    error_rate_pct
from {{ ref('mart_service_hourly_kpis') }}
where error_rate_pct < 0 or error_rate_pct > 100
