-- Daily active users and request volume per service.

with events as (
    select * from {{ ref('stg_events') }}
)

select
    event_date,
    service,
    count(distinct user_id)                          as active_users,
    count(*)                                         as total_requests,
    round(count(*) * 1.0 / count(distinct user_id), 1) as requests_per_user
from events
group by event_date, service
