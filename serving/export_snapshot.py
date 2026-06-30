"""
Export the dashboard's analytics queries to static JSON files.

Runs the four Gold-mart queries once (using local AWS credentials) and
writes the results as JSON, so the dashboard can be deployed as a static
site with no backend and no credentials. Re-run this to refresh the snapshot.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from app import queries

OUT = Path(__file__).parent / "static_site" / "data"
OUT.mkdir(parents=True, exist_ok=True)


def records(df):
    return df.to_dict(orient="records")


def main():
    # Run each query and shape it exactly as the live API does.
    service_health = records(queries.service_health())

    trend = queries.error_rate_trend()
    trend["label"] = (
        trend["event_date"].astype(str) + " "
        + trend["event_hour"].astype(str).str.zfill(2) + ":00"
    )
    error_trend = records(trend)

    latency = records(queries.latency_percentiles())
    active_users = records(queries.daily_active_users())

    datasets = {
        "service-health": service_health,
        "error-trend": error_trend,
        "latency": latency,
        "active-users": active_users,
    }
    for name, data in datasets.items():
        (OUT / f"{name}.json").write_text(json.dumps(data, default=str, indent=2))
        print(f"wrote {name}.json ({len(data)} rows)")

    # A small metadata file so the page can show when the snapshot was taken.
    (OUT / "meta.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }))
    print("snapshot complete:", OUT)


if __name__ == "__main__":
    main()
