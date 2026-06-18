"""
Synthetic application log generator for PipelineWatch.

Generates realistic-looking telemetry events and writes them to S3 Bronze
in Hive-style partitioned layout, ready for downstream processing by Glue
and Athena.
"""
import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import boto3
from faker import Faker

fake = Faker()

# ---------------------------------------------------------------------
# Domain model: simulated services and their endpoints.
# Modeled after a typical microservices SaaS — auth, payments, search,
# notifications, user management.
# ---------------------------------------------------------------------
SERVICES = ["auth-api", "payments-api", "search-api", "notification-svc", "user-svc"]

ENDPOINTS = {
    "auth-api": ["/login", "/logout", "/refresh", "/verify"],
    "payments-api": ["/charge", "/refund", "/status", "/list"],
    "search-api": ["/search", "/autocomplete", "/suggest"],
    "notification-svc": ["/send-email", "/send-sms", "/send-push"],
    "user-svc": ["/profile", "/update", "/delete", "/preferences"],
}

# Weighted distribution: real traffic is overwhelmingly successful.
# 70% 200, 10% 201, ~20% errors (4xx + 5xx).
STATUS_CODES = [200] * 70 + [201] * 10 + [400] * 8 + [404] * 5 + [500] * 5 + [503] * 2

REGIONS = ["ap-south-1", "us-east-1", "eu-west-1", "ap-southeast-1"]

METHODS = ["GET", "GET", "GET", "POST", "POST", "PUT", "DELETE"]


def generate_event(timestamp: datetime) -> dict:
    """Generate a single realistic log event."""
    service = random.choice(SERVICES)
    endpoint = random.choice(ENDPOINTS[service])
    status = random.choice(STATUS_CODES)

    # Errors tend to be slower than successes (timeouts, retries, etc.)
    is_error = status >= 500
    latency = random.randint(1000, 5000) if is_error else random.randint(5, 800)

    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": timestamp.isoformat(),
        "service": service,
        "endpoint": endpoint,
        "method": random.choice(METHODS),
        "status_code": status,
        "latency_ms": latency,
        "user_id": f"user_{random.randint(1, 10000)}",
        "region": random.choice(REGIONS),
        "ip": fake.ipv4(),
        "error_message": fake.sentence() if is_error else None,
    }


def generate_hour_of_events(
    hour_start: datetime,
    events_per_hour: int = 5000,
) -> list[dict]:
    """Generate a sorted list of events spread across one hour."""
    events = []
    for _ in range(events_per_hour):
        offset_seconds = random.uniform(0, 3600)
        ts = hour_start + timedelta(seconds=offset_seconds)
        events.append(generate_event(ts))
    events.sort(key=lambda e: e["timestamp"])
    return events


def write_partition_to_s3(
    events: list[dict],
    bucket: str,
    service: str,
    ts: datetime,
) -> str:
    """Write events for one (service, hour) partition to S3 as JSONL.

    Returns the S3 key written.
    """
    key = (
        f"bronze/"
        f"service={service}/"
        f"year={ts.year}/"
        f"month={ts.month:02d}/"
        f"day={ts.day:02d}/"
        f"hour={ts.hour:02d}/"
        f"events_{uuid.uuid4().hex[:8]}.jsonl"
    )
    body = "\n".join(json.dumps(e) for e in events)
    s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=body.encode("utf-8"))
    return key


def run(
    bucket: str,
    events_per_hour: int = 5000,
    target_hour: Optional[datetime] = None,
) -> None:
    """Generate one hour of events and partition them by service before writing."""
    if target_hour is None:
        target_hour = datetime.now(timezone.utc).replace(
            minute=0, second=0, microsecond=0
        )

    print(f"Generating {events_per_hour} events for hour {target_hour.isoformat()}")
    events = generate_hour_of_events(target_hour, events_per_hour)

    # Partition by service before writing — one file per (service, hour).
    # This matches how Glue and Athena prefer to read data.
    by_service: dict[str, list[dict]] = {}
    for event in events:
        by_service.setdefault(event["service"], []).append(event)

    for service, service_events in by_service.items():
        key = write_partition_to_s3(service_events, bucket, service, target_hour)
        print(f"  Wrote {len(service_events):>4} events -> s3://{bucket}/{key}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_logs.py <bronze-bucket-name> [events_per_hour]")
        sys.exit(1)
    bucket_name = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    run(bucket_name, events_per_hour=n)