"""HTTP helpers and a sync-logging context manager shared by sync tasks."""
import time
from contextlib import contextmanager

import requests
from django.conf import settings
from django.core.cache import cache

from .models import SyncLog

# football-data.org competition codes for the leagues we cover (PRD data sources).
FOOTBALL_DATA_COMPETITIONS = {
    "PL": "Premier League",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "CL": "UEFA Champions League",
}

# API-Football league id for Indonesian Liga 1.
API_FOOTBALL_LIGA1_ID = 274

API_FOOTBALL_DAILY_CAP = 90  # abort before the real 100/day quota
API_FOOTBALL_COUNTER_KEY = "api_football:daily_count"


def football_data_get(path, params=None):
    """GET football-data.org. Sleeps 6s to respect the 10 req/min free limit."""
    url = f"{settings.FOOTBALL_DATA_BASE_URL}/{path.lstrip('/')}"
    headers = {"X-Auth-Token": settings.FOOTBALL_DATA_API_KEY}
    resp = requests.get(url, headers=headers, params=params or {}, timeout=30)
    resp.raise_for_status()
    time.sleep(6)  # rate-limit safety — stay under 10 req/min
    return resp.json()


def api_football_get(path, params=None):
    """GET API-Football, tracking daily request count in Redis to conserve quota."""
    count = cache.get(API_FOOTBALL_COUNTER_KEY, 0)
    if count >= API_FOOTBALL_DAILY_CAP:
        raise RuntimeError(
            f"API-Football daily cap reached ({count}/{API_FOOTBALL_DAILY_CAP}); aborting."
        )
    url = f"{settings.API_FOOTBALL_BASE_URL}/{path.lstrip('/')}"
    headers = {"x-apisports-key": settings.API_FOOTBALL_KEY}
    resp = requests.get(url, headers=headers, params=params or {}, timeout=30)
    resp.raise_for_status()
    # Increment with a 24h TTL so the counter resets daily.
    cache.set(API_FOOTBALL_COUNTER_KEY, count + 1, timeout=60 * 60 * 24)
    return resp.json()


@contextmanager
def sync_logger(task: str, target: str = ""):
    """Context manager that records a SyncLog row with counts and duration.

    Usage:
        with sync_logger("sync_standings", target=league.name) as log:
            ...
            log["created"] += 1
            log["updated"] += 1
    """
    started = time.monotonic()
    counters = {"created": 0, "updated": 0, "errors": []}
    success = True
    try:
        yield counters
    except Exception as exc:  # noqa: BLE001 — record then re-raise for Celery retry
        success = False
        counters["errors"].append(repr(exc))
        raise
    finally:
        SyncLog.objects.create(
            task=task,
            target=target,
            records_created=counters["created"],
            records_updated=counters["updated"],
            errors="\n".join(counters["errors"]),
            duration_ms=int((time.monotonic() - started) * 1000),
            success=success,
        )
