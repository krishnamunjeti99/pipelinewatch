-- Error breakdown by service, endpoint, and status code.

with errors as (
    select * from {{ ref('stg_events') }}
    where is_error
)

select
    service,
    endpoint,
    status_code,
    count(*)                            as error_count,
    count(distinct user_id)             as affected_users,
    approx_percentile(latency_ms, 0.95) as p95_latency_ms
from errors
group by service, endpoint, status_code
order by error_count desc
