-- Hourly service health KPIs: volume, errors, latency percentiles.
-- Materialized as a table (per dbt_project.yml marts default).
-- Built on stg_events via ref() -> dbt sets the build order automatically.

with events as (
    select * from {{ ref('stg_events') }}
)

select
    service,
    event_date,
    event_hour,
    count(*)                                                          as total_requests,
    sum(case when is_error then 1 else 0 end)                        as error_count,
    sum(case when is_server_error then 1 else 0 end)                 as server_error_count,
    round(100.0 * sum(case when is_error then 1 else 0 end)
          / count(*), 2)                                              as error_rate_pct,
    round(avg(latency_ms), 1)                                         as avg_latency_ms,
    approx_percentile(latency_ms, 0.50)                               as p50_latency_ms,
    approx_percentile(latency_ms, 0.95)                               as p95_latency_ms,
    approx_percentile(latency_ms, 0.99)                               as p99_latency_ms,
    count(distinct user_id)                                           as unique_users
from events
group by service, event_date, event_hour
