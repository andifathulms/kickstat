"""Ingest free xG data from Understat for the top-5 European leagues (2014+).

    python manage.py ingest_understat --league EPL --season 2023
    python manage.py ingest_understat --all

Understat embeds each league-season's matches as a hex-escaped JSON blob
(``datesData``) in the page HTML. We extract per-match team xG — the most-wanted
stat football-data.co.uk lacks — and store it as historical matches with stats.

Understat is an unofficial source; this is for personal/research use.
"""
import codecs
import json
import re
import time
from datetime import datetime, timezone

import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.leagues.models import League, Source, Team
from apps.matches.models import Match, MatchStats, MatchStatus

BASE_URL = "https://understat.com/league"

# Understat league code -> (display name, country)
LEAGUES = {
    "EPL": ("Premier League", "England"),
    "La_liga": ("La Liga", "Spain"),
    "Bundesliga": ("Bundesliga", "Germany"),
    "Serie_A": ("Serie A", "Italy"),
    "Ligue_1": ("Ligue 1", "France"),
}
SEASONS = list(range(2014, 2025))  # 2014/15 .. 2024/25

_DATES_RE = re.compile(r"datesData\s*=\s*JSON\.parse\('([^']+)'\)")


def decode_dates_data(html: str):
    """Extract and decode the ``datesData`` JSON blob from Understat HTML."""
    m = _DATES_RE.search(html)
    if not m:
        return []
    decoded = codecs.decode(m.group(1), "unicode_escape")
    try:
        decoded = decoded.encode("latin-1").decode("utf-8")  # fix accented names
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    return json.loads(decoded)


def fetch_dates_data(league: str, season: int, retries: int = 3):
    url = f"{BASE_URL}/{league}/{season}"
    headers = {"User-Agent": "Mozilla/5.0 (Kickstat data ingest)"}
    last = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()
            return decode_dates_data(resp.text)
        except requests.RequestException as exc:
            last = exc
            if attempt < retries:
                time.sleep(attempt * 3)
    raise last


class Command(BaseCommand):
    help = "Ingest Understat xG for the top-5 leagues."

    def add_arguments(self, parser):
        parser.add_argument("--league", choices=list(LEAGUES))
        parser.add_argument("--season", type=int)
        parser.add_argument("--all", action="store_true")

    def handle(self, *args, **options):
        if options["all"]:
            pairs = [(lg, yr) for lg in LEAGUES for yr in SEASONS]
        else:
            if not options["league"] or not options["season"]:
                raise CommandError("Provide --league and --season, or use --all.")
            pairs = [(options["league"], options["season"])]

        grand = 0
        for league_code, season in pairs:
            grand += self._ingest(league_code, season)
        self.stdout.write(self.style.SUCCESS(f"Ingested {grand} matches with xG."))

    def _league_row(self, league_code, season):
        name, country = LEAGUES[league_code]
        league, _ = League.objects.update_or_create(
            source=Source.FOOTBALL_DATA,
            external_id=f"understat-{league_code}-{season}",
            defaults={
                "name": f"{name} (Understat {season})",
                "slug": slugify(f"{name} understat {season}"),
                "country": country,
                "season": str(season),
                "is_active": False,
            },
        )
        return league

    def _team(self, obj, league):
        team, _ = Team.objects.update_or_create(
            source=Source.FOOTBALL_DATA,
            external_id=f"us-{obj['id']}",
            defaults={"name": obj["title"], "league": league},
        )
        return team

    def _ingest(self, league_code, season):
        self.stdout.write(f"Fetching Understat {league_code} {season}")
        try:
            entries = fetch_dates_data(league_code, season)
        except requests.RequestException as exc:
            self.stderr.write(f"  skipped: {exc}")
            return 0
        league = self._league_row(league_code, season)
        count = 0
        for e in entries:
            if not e.get("isResult"):
                continue  # skip not-yet-played fixtures
            count += self._ingest_entry(e, league)
        self.stdout.write(f"  {count} matches")
        return count

    def _ingest_entry(self, e, league):
        home = self._team(e["h"], league)
        away = self._team(e["a"], league)
        kickoff = datetime.strptime(e["datetime"], "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
        match, _ = Match.objects.update_or_create(
            external_id=f"understat-{e['id']}",
            defaults={
                "league": league,
                "home_team": home,
                "away_team": away,
                "kickoff": kickoff,
                "status": MatchStatus.FINISHED,
                "home_score": int(e["goals"]["h"]),
                "away_score": int(e["goals"]["a"]),
                "raw_data": e,
            },
        )
        MatchStats.objects.update_or_create(
            match=match,
            defaults={
                "home_xg": round(float(e["xG"]["h"]), 3),
                "away_xg": round(float(e["xG"]["a"]), 3),
            },
        )
        return 1
