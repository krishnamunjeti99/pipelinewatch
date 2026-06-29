"""
PipelineWatch analytics dashboard — FastAPI backend.

Serves analytics from the Gold marts as JSON endpoints,
plus the dashboard HTML page itself.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import queries

app = FastAPI(title="PipelineWatch Analytics")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def dashboard():
    """Serve the dashboard page."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/service-health")
def api_service_health():
    return queries.service_health().to_dict(orient="records")


@app.get("/api/error-trend")
def api_error_trend():
    df = queries.error_rate_trend()
    df["label"] = df["event_date"].astype(str) + " " + df["event_hour"].astype(str).str.zfill(2) + ":00"
    return df.to_dict(orient="records")


@app.get("/api/latency")
def api_latency():
    return queries.latency_percentiles().to_dict(orient="records")


@app.get("/api/active-users")
def api_active_users():
    return queries.daily_active_users().to_dict(orient="records")
