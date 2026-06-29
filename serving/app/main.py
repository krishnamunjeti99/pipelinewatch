"""
PipelineWatch analytics dashboard — FastAPI backend.

Serves analytics from the Gold marts as JSON endpoints.
The HTML dashboard (Day 3) consumes these endpoints.
"""
from fastapi import FastAPI

from app import queries

app = FastAPI(title="PipelineWatch Analytics")


@app.get("/health")
def health():
    """Liveness check."""
    return {"status": "ok"}


@app.get("/api/service-health")
def api_service_health():
    df = queries.service_health()
    return df.to_dict(orient="records")


@app.get("/api/error-trend")
def api_error_trend():
    df = queries.error_rate_trend()
    # Build a readable time label for charting
    df["label"] = df["event_date"].astype(str) + " " + df["event_hour"].astype(str).str.zfill(2) + ":00"
    return df.to_dict(orient="records")


@app.get("/api/latency")
def api_latency():
    df = queries.latency_percentiles()
    return df.to_dict(orient="records")


@app.get("/api/active-users")
def api_active_users():
    df = queries.daily_active_users()
    return df.to_dict(orient="records")
