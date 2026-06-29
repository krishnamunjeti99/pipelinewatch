"""
Analytics queries against the Gold marts.

Each function answers one business question and returns a DataFrame.
These read pre-aggregated Gold tables, so they are cheap and fast.
"""
from app.athena import query


def service_health() -> "pd.DataFrame":
    """Per-service health: requests, error rate, P95 latency.
    Aggregates the hourly KPI mart up to the service level."""
    sql = """
        SELECT
            service,
            SUM(total_requests)                       AS total_requests,
            SUM(error_count)                          AS total_errors,
            ROUND(100.0 * SUM(error_count)
                  / SUM(total_requests), 2)           AS error_rate_pct,
            ROUND(AVG(p95_latency_ms), 0)             AS avg_p95_latency_ms,
            SUM(unique_users)                         AS user_events
        FROM mart_service_hourly_kpis
        GROUP BY service
        ORDER BY error_rate_pct DESC
    """
    return query(sql)


def error_rate_trend() -> "pd.DataFrame":
    """Hourly error rate across all services (the 'is it getting worse' view)."""
    sql = """
        SELECT
            event_date,
            event_hour,
            SUM(total_requests)                       AS total_requests,
            ROUND(100.0 * SUM(error_count)
                  / SUM(total_requests), 2)           AS error_rate_pct
        FROM mart_service_hourly_kpis
        GROUP BY event_date, event_hour
        ORDER BY event_date, event_hour
    """
    return query(sql)


def latency_percentiles() -> "pd.DataFrame":
    """Average P50/P95/P99 latency by service."""
    sql = """
        SELECT
            service,
            ROUND(AVG(p50_latency_ms), 0) AS p50,
            ROUND(AVG(p95_latency_ms), 0) AS p95,
            ROUND(AVG(p99_latency_ms), 0) AS p99
        FROM mart_service_hourly_kpis
        GROUP BY service
        ORDER BY p95 DESC
    """
    return query(sql)


def daily_active_users() -> "pd.DataFrame":
    """Active users and request volume per day."""
    sql = """
        SELECT
            event_date,
            SUM(active_users)   AS active_users,
            SUM(total_requests) AS total_requests
        FROM mart_daily_active_users
        GROUP BY event_date
        ORDER BY event_date
    """
    return query(sql)
