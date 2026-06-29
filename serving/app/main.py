"""
PipelineWatch analytics dashboard — FastAPI backend.

Serves analytics from the Gold marts as JSON, plus the dashboard page.
Query results are cached in-memory with a short TTL for responsiveness.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import queries
from app.cache import cached, clear

app = FastAPI(title="PipelineWatch Analytics")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/service-health")
def api_service_health():
    df = cached("service_health", queries.service_health)
    return df.to_dict(orient="records")


@app.get("/api/error-trend")
def api_error_trend():
    df = cached("error_trend", queries.error_rate_trend).copy()
    df["label"] = df["event_date"].astype(str) + " " + df["event_hour"].astype(str).str.zfill(2) + ":00"
    return df.to_dict(orient="records")


@app.get("/api/latency")
def api_latency():
    df = cached("latency", queries.latency_percentiles)
    return df.to_dict(orient="records")


@app.get("/api/active-users")
def api_active_users():
    df = cached("active_users", queries.daily_active_users)
    return df.to_dict(orient="records")


@app.post("/api/refresh")
def api_refresh():
    """Clear the cache so the next load re-queries Athena for fresh data."""
    clear()
    return {"status": "cache cleared"}
