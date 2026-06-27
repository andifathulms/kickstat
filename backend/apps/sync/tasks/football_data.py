"""Celery sync tasks for football-data.org (European leagues).

Every task is idempotent: it uses ``update_or_create`` keyed on ``external_id``.
The ``football_data_get`` helper already sleeps 6s per request to respect the
10 req/min free-tier limit.
"""
from datetime import datetime, timedelta, timezone

from celery import shared_task

from apps.leagues.models import League, Source, Standing, Team
from apps.matches.models import Match, MatchStatus

from ..client import FOOTBALL_DATA_COMPETITIONS, football_data_get, sync_logger

# football-data.org status -> our MatchStatus
_STATUS_MAP = {
    "SCHEDULED": MatchStatus.SCHEDULED,
    "TIMED": MatchStatus.SCHEDULED,
    "IN_PLAY": MatchStatus.LIVE,
    "PAUSED": MatchStatus.LIVE,
    "FINISHED": MatchStatus.FINISHED,
    "AWARDED": MatchStatus.FINISHED,
    "POSTPONED": MatchStatus.POSTPONED,
    "SUSPENDED": MatchStatus.POSTPONED,
    "CANCELLED": MatchStatus.CANCELLED,
}


def _parse_dt(value):
    """Parse an ISO8601 UTC timestamp from the API into an aware datetime."""
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _upsert_team(team_data, league, counters):
    """Upsert a Team from a football-data.org team object."""
    ext = str(team_data["id"])
    team, created = Team.objects.update_or_create(
        source=Source.FOOTBALL_DATA,
        external_id=ext,
        defaults={
            "name": team_data.get("name") or team_data.get("shortName") or "Unknown",
            "short_name": team_data.get("tla") or team_data.get("shortName") or "",
            "logo_url": team_data.get("crest") or "",
            "league": league,
        },
    )
    counters["created" if created else "updated"] += 1
    return team


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_leagues(self):
    """Pull and upsert all covered competitions as League rows."""
    try:
        with sync_logger("sync_leagues") as counters:
            for code, name in FOOTBALL_DATA_COMPETITIONS.items():
                data = football_data_get(f"competitions/{code}")
                season = ""
                cs = data.get("currentSeason") or {}
                if cs.get("startDate"):
                    season = cs["startDate"][:4]
                _, created = League.objects.update_or_create(
                    source=Source.FOOTBALL_DATA,
                    external_id=code,
                    defaults={
                        "name": data.get("name", name),
                        "country": (data.get("area") or {}).get("name", ""),
                        "season": season,
                        "is_active": True,
                    },
                )
                counters["created" if created else "updated"] += 1
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_standings(self, league_id: int):
    """Upsert standings for one league."""
    league = League.objects.get(pk=league_id)
    try:
        with sync_logger("sync_standings", target=league.name) as counters:
            data = football_data_get(f"competitions/{league.external_id}/standings")
            season = str((data.get("season") or {}).get("startDate", "") or "")[:4]
            for block in data.get("standings", []):
                if block.get("type") != "TOTAL":
                    continue
                for row in block.get("table", []):
                    team = _upsert_team(row["team"], league, counters)
                    _, created = Standing.objects.update_or_create(
                        league=league,
                        team=team,
                        season=season or league.season,
                        defaults={
                            "position": row["position"],
                            "played": row["playedGames"],
                            "won": row["won"],
                            "drawn": row["draw"],
                            "lost": row["lost"],
                            "goals_for": row["goalsFor"],
                            "goals_against": row["goalsAgainst"],
                            "goal_difference": row["goalDifference"],
                            "points": row["points"],
                        },
                    )
                    counters["created" if created else "updated"] += 1
    except Exception as exc:
        raise self.retry(exc=exc)


def _upsert_match(m, league, counters):
    """Upsert a single Match from a football-data.org match object."""
    home = _upsert_team(m["homeTeam"], league, counters)
    away = _upsert_team(m["awayTeam"], league, counters)
    full = (m.get("score") or {}).get("fullTime") or {}
    _, created = Match.objects.update_or_create(
        external_id=str(m["id"]),
        defaults={
            "league": league,
            "home_team": home,
            "away_team": away,
            "matchday": m.get("matchday"),
            "kickoff": _parse_dt(m.get("utcDate")),
            "status": _STATUS_MAP.get(m.get("status"), MatchStatus.SCHEDULED),
            "home_score": full.get("home"),
            "away_score": full.get("away"),
            "raw_data": m,
        },
    )
    counters["created" if created else "updated"] += 1


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_fixtures(self, league_id: int, days_ahead: int = 7):
    """Upsert upcoming fixtures for one league within the next ``days_ahead`` days."""
    league = League.objects.get(pk=league_id)
    today = datetime.now(timezone.utc).date()
    params = {
        "dateFrom": today.isoformat(),
        "dateTo": (today + timedelta(days=days_ahead)).isoformat(),
    }
    try:
        with sync_logger("sync_fixtures", target=league.name) as counters:
            data = football_data_get(
                f"competitions/{league.external_id}/matches", params=params
            )
            for m in data.get("matches", []):
                _upsert_match(m, league, counters)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_results(self, league_id: int, days_back: int = 3):
    """Upsert recently finished matches (and their scores) for one league."""
    league = League.objects.get(pk=league_id)
    today = datetime.now(timezone.utc).date()
    params = {
        "dateFrom": (today - timedelta(days=days_back)).isoformat(),
        "dateTo": today.isoformat(),
        "status": "FINISHED",
    }
    try:
        with sync_logger("sync_results", target=league.name) as counters:
            data = football_data_get(
                f"competitions/{league.external_id}/matches", params=params
            )
            for m in data.get("matches", []):
                _upsert_match(m, league, counters)
    except Exception as exc:
        raise self.retry(exc=exc)


# --- Aggregate tasks used by Celery Beat -----------------------------------

def _football_data_league_ids():
    return list(
        League.objects.filter(
            source=Source.FOOTBALL_DATA, is_active=True
        ).values_list("id", flat=True)
    )


@shared_task
def sync_all_standings():
    for lid in _football_data_league_ids():
        sync_standings.delay(lid)


@shared_task
def sync_all_fixtures():
    for lid in _football_data_league_ids():
        sync_fixtures.delay(lid)


@shared_task
def sync_all_results():
    for lid in _football_data_league_ids():
        sync_results.delay(lid)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def sync_live_scores(self):
    """Refresh currently in-play matches across all football-data.org leagues.

    Only active on matchdays: if no matches are LIVE, this is a single cheap call.
    """
    try:
        with sync_logger("sync_live_scores") as counters:
            data = football_data_get("matches", params={"status": "IN_PLAY,PAUSED"})
            matches = data.get("matches", [])
            for m in matches:
                comp_code = (m.get("competition") or {}).get("code")
                league = League.objects.filter(
                    source=Source.FOOTBALL_DATA, external_id=comp_code
                ).first()
                if league:
                    _upsert_match(m, league, counters)
    except Exception as exc:
        raise self.retry(exc=exc)
