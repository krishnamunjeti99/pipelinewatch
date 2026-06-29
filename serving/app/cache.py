"""
Tiny in-memory TTL cache for dashboard queries.

Athena queries are slow (seconds) and cost money per run. Dashboard
metrics don't need real-time freshness, so we cache results for a few
minutes. Trade-off: data can be up to TTL_SECONDS stale — acceptable
for a metrics view, and a large win in responsiveness and cost.
"""
import time
from typing import Callable

import pandas as pd

TTL_SECONDS = 300  # 5 minutes

_store: dict[str, tuple[float, pd.DataFrame]] = {}


def cached(key: str, producer: Callable[[], pd.DataFrame]) -> pd.DataFrame:
    """Return a cached DataFrame for `key`, or compute + store it if
    missing or expired."""
    now = time.time()
    if key in _store:
        ts, df = _store[key]
        if now - ts < TTL_SECONDS:
            return df
    df = producer()
    _store[key] = (now, df)
    return df


def clear() -> None:
    """Clear the cache (e.g. for a manual refresh)."""
    _store.clear()
