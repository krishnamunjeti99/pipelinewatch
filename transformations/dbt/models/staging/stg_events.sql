-- Staging model: light standardization over the Silver source.
-- Materialized as a view (per dbt_project.yml default for staging/).

select
    event_id,
    event_ts,
    event_date,
    event_hour,
    service,
    endpoint,
    method,
    status_code,
    latency_ms,
    user_id,
    region,
    is_error,
    is_server_error
from {{ source('lakehouse', 'silver') }}
