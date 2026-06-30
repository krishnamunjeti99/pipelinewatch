"""
Synthetic application log generator for PipelineWatch.
"""
import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

import boto3
from faker import Faker

fake = Faker()

SERVICES = ["auth-api", "payments-api", "search-api", "notification-svc", "user-svc"]

ENDPOINTS = {
    "auth-api": ["/login", "/logout", "/refresh", "/verify"],
    "payments-api": ["/charge", "/refund", "/status", "/list"],
    "search-api": ["/search", "/autocomplete", "/suggest"],
    "notification-svc": ["/send-email", "/send-sms", "/send-push"],
    "user-svc": ["/profile", "/update", "/delete", "/preferences"],
}

STATUS_CODES = [200] * 70 + [201] * 10 + [400] * 8 + [404] * 5 + [500] * 5 + [503] * 2
REGIONS = ["ap-south-1", "us-east-1", "eu-west-1", "ap-southeast-1"]
METHODS = ["GET", "GET", "GET", "POST", "POST", "PUT", "DELETE"]


def generate_event(timestamp):
    service = random.choice(SERVICES)
    endpoint = random.choice(ENDPOINTS[service])
    status = random.choice(STATUS_CODES)
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


def generate_hour_of_events(hour_start, events_per_hour=5000):
    events = []
    for _ in range(events_per_hour):
        offset = random.uniform(0, 3600)
        events.append(generate_event(hour_start + timedelta(seconds=offset)))
    events.sort(key=lambda e: e["timestamp"])
    return events


def write_partition_to_s3(events, bucket, service, ts):
    key = (
        f"bronze/service={service}/"
        f"year={ts.year}/month={ts.month:02d}/day={ts.day:02d}/hour={ts.hour:02d}/"
        f"events_{uuid.uuid4().hex[:8]}.jsonl"
    )
    body = "\n".join(json.dumps(e) for e in events)
    boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=body.encode("utf-8"))
    return key


def run(bucket, events_per_hour=5000, target_hour=None):
    if target_hour is None:
        target_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    print(f"Generating {events_per_hour} events for hour {target_hour.isoformat()}")
    events = generate_hour_of_events(target_hour, events_per_hour)
    by_service = {}
    for e in events:
        by_service.setdefault(e["service"], []).append(e)
    for service, svc_events in by_service.items():
        key = write_partition_to_s3(svc_events, bucket, service, target_hour)
        print(f"  Wrote {len(svc_events):>4} events -> s3://{bucket}/{key}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_logs.py <bucket> [--backfill N] [--events N]")
        sys.exit(1)

    bucket_name = sys.argv[1]
    args = sys.argv[2:]
    backfill_hours = 0
    events_per_hour = 5000

    i = 0
    while i < len(args):
        if args[i] == "--backfill" and i + 1 < len(args):
            backfill_hours = int(args[i + 1])
            i += 2
        elif args[i] == "--events" and i + 1 < len(args):
            events_per_hour = int(args[i + 1])
            i += 2
        else:
            print(f"Unknown argument: {args[i]}")
            sys.exit(1)

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    if backfill_hours > 0:
        print(f"Backfilling {backfill_hours} hours ({events_per_hour} events/hour)")
        for h in range(backfill_hours):
            run(bucket_name, events_per_hour, now - timedelta(hours=h))
        print(f"Done: {backfill_hours * events_per_hour} total events")
    else:
        run(bucket_name, events_per_hour)
