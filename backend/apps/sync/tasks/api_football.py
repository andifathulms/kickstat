"""Celery sync tasks for API-Football — Indonesian Liga 1 only.

The free tier allows 100 req/day, so Liga 1 is synced sparingly (weekly fixtures,
daily results). ``api_football_get`` tracks a daily counter in Redis and aborts
before the quota is exhausted.
"""
from datetime import datetime, timezone

from celery import shared_task
from django.utils.text import slugify

from apps.leagues.models import League, Source, Team
from apps.matches.models import Match, MatchStatus

from ..client import API_FOOTBALL_LIGA1_ID, api_football_get, sync_logger

# API-Football fixture status short codes -> our MatchStatus
_STATUS_MAP = {
    "TBD": MatchStatus.SCHEDULED,
    "NS": MatchStatus.SCHEDULED,
    "1H": MatchStatus.LIVE,
    "HT": MatchStatus.LIVE,
    "2H": MatchStatus.LIVE,
    "ET": MatchStatus.LIVE,
    "P": MatchStatus.LIVE,
    "LIVE": MatchStatus.LIVE,
    "FT": MatchStatus.FINISHED,
    "AET": MatchStatus.FINISHED,
    "PEN": MatchStatus.FINISHED,
    "PST": MatchStatus.POSTPONED,
    "CANC": MatchStatus.CANCELLED,
    "ABD": MatchStatus.CANCELLED,
}

CURRENT_SEASON = "2025"


def _get_or_create_liga1():
    league, _ = League.objects.update_or_create(
        source=Source.API_FOOTBALL,
        external_id=str(API_FOOTBALL_LIGA1_ID),
        defaults={
            "name": "Liga 1",
            "slug": slugify("Liga 1 Indonesia"),
            "country": "Indonesia",
            "season": CURRENT_SEASON,
            "is_active": True,
        },
    )
    return league


def _parse_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _upsert_team(team_data, league, counters):
    ext = str(team_data["id"])
    team, created = Team.objects.update_or_create(
        source=Source.API_FOOTBALL,
        external_id=ext,
        defaults={
            "name": team_data.get("name", "Unknown"),
            "logo_url": team_data.get("logo") or "",
            "league": league,
        },
    )
    counters["created" if created else "updated"] += 1
    return team


def _upsert_fixture(item, league, counters):
    fixture = item["fixture"]
    teams = item["teams"]
    goals = item.get("goals") or {}
    home = _upsert_team(teams["home"], league, counters)
    away = _upsert_team(teams["away"], league, counters)
    status_short = (fixture.get("status") or {}).get("short")
    _, created = Match.objects.update_or_create(
        external_id=str(fixture["id"]),
        defaults={
            "league": league,
            "home_team": home,
            "away_team": away,
            "matchday": (item.get("league") or {}).get("round_number"),
            "kickoff": _parse_dt(fixture.get("date")),
            "status": _STATUS_MAP.get(status_short, MatchStatus.SCHEDULED),
            "home_score": goals.get("home"),
            "away_score": goals.get("away"),
            "raw_data": item,
        },
    )
    counters["created" if created else "updated"] += 1


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def sync_liga1_fixtures(self):
    """Sync upcoming Liga 1 fixtures (run weekly to conserve quota)."""
    league = _get_or_create_liga1()
    try:
        with sync_logger("sync_liga1_fixtures", target=league.name) as counters:
            data = api_football_get(
                "fixtures",
                params={
                    "league": API_FOOTBALL_LIGA1_ID,
                    "season": CURRENT_SEASON,
                    "next": 30,
                },
            )
            for item in data.get("response", []):
                _upsert_fixture(item, league, counters)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def sync_liga1_results(self):
    """Sync recent Liga 1 results (run daily on Liga 1 matchdays)."""
    league = _get_or_create_liga1()
    today = datetime.now(timezone.utc).date().isoformat()
    try:
        with sync_logger("sync_liga1_results", target=league.name) as counters:
            data = api_football_get(
                "fixtures",
                params={
                    "league": API_FOOTBALL_LIGA1_ID,
                    "season": CURRENT_SEASON,
                    "date": today,
                },
            )
            for item in data.get("response", []):
                _upsert_fixture(item, league, counters)
    except Exception as exc:
        raise self.retry(exc=exc)
