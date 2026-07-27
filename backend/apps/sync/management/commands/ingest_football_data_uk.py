"""Ingest free historical match stats from football-data.co.uk.

    python manage.py ingest_football_data_uk --division E0 --season 2324
    python manage.py ingest_football_data_uk --division E0 --season 2324 2223 2122

football-data.co.uk publishes free CSVs (no API key) with per-match shots,
shots-on-target, corners, fouls, and cards for the major European leagues going
back decades. football-data.org's free tier has none of these, so this fills the
``MatchStats`` gap and gives the ML pipeline far more history to train on.

Data is stored as historical, non-live matches: one umbrella League per division
(``is_active=False``) with teams kept stable across seasons by normalised name.
"""
import csv
import io
import time
from datetime import datetime, timezone

import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.leagues.models import League, Source, Team
from apps.matches.models import Match, MatchStats, MatchStatus, Referee

BASE_URL = "https://www.football-data.co.uk/mmz4281"

# Be polite to the static file host and resilient to transient errors. The
# retry budget is generous because the path to this host is genuinely flaky:
# on top of its broken certificate, ISP-level filtering intermittently answers
# with a redirect to a block page or a MITM'd certificate, so an individual
# attempt fails often enough that three is not enough to get a season through.
REQUEST_DELAY_SECONDS = 0.5
MAX_RETRIES = 8

# These files carry a UTF-8 BOM but are decoded as latin-1 (the encoding the
# rest of the file needs), which turns those three bytes into "ï»¿" rather than
# U+FEFF. Both spellings have to be recognised.
BOM_PREFIXES = ("﻿", "ï»¿")


def looks_like_csv(text):
    """Guard against a response that is HTML wearing a .csv URL.

    Some ISPs intercept plain-HTTP-ish requests and answer with a redirect to a
    filtering portal, which requests follows silently. The result parses as a
    zero-row CSV, so the ingest would report "0 matches" for a season that is
    perfectly fine upstream. Every football-data.co.uk file starts with the
    same header, so check for it and treat anything else as a failed fetch.
    """
    if text is None:
        return False
    head = text.lstrip()
    for bom in BOM_PREFIXES:
        if head.startswith(bom):
            head = head[len(bom):]
            break
    return head.startswith("Div,")


def fetch_csv(url):
    """Download a CSV with retries. Returns text, or None if the file is absent.

    404 means the division/season doesn't exist -> skip (no retry). Transient
    failures (timeouts, SSL, 5xx, rate-limit, interception) are retried with
    backoff.
    """
    # The host's TLS certificate does not cover www.football-data.co.uk, so
    # verification fails. These are public, unauthenticated static CSVs — fall
    # back to an unverified fetch rather than losing the source entirely.
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=60)
        except requests.exceptions.SSLError:
            try:
                resp = requests.get(url, timeout=60, verify=False)
            except requests.RequestException:
                if attempt == MAX_RETRIES:
                    return None
                time.sleep(attempt * 2)
                continue
        except requests.RequestException:
            if attempt == MAX_RETRIES:
                return None
            time.sleep(attempt * 2)
            continue
        if resp.status_code == 404:
            return None
        if resp.status_code == 200:
            text = resp.content.decode("latin-1")
            if looks_like_csv(text):
                return text
        # 403/429/5xx, or an intercepted response -> back off and retry
        if attempt == MAX_RETRIES:
            return None
        time.sleep(attempt * 2)
    return None

# football-data.co.uk division code -> (display name, country)
DIVISIONS = {
    "E0": ("Premier League", "England"),
    "E1": ("Championship", "England"),
    "SP1": ("La Liga", "Spain"),
    "SP2": ("Segunda División", "Spain"),
    "I1": ("Serie A", "Italy"),
    "I2": ("Serie B", "Italy"),
    "D1": ("Bundesliga", "Germany"),
    "D2": ("2. Bundesliga", "Germany"),
    "F1": ("Ligue 1", "France"),
    "F2": ("Ligue 2", "France"),
    "N1": ("Eredivisie", "Netherlands"),
    "P1": ("Primeira Liga", "Portugal"),
    "SC0": ("Scottish Premiership", "Scotland"),
    "B1": ("Belgian Pro League", "Belgium"),
    "T1": ("Süper Lig", "Turkey"),
    "G1": ("Super League", "Greece"),
}


def _to_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_date(date_str, time_str):
    """football-data.co.uk uses dd/mm/yy or dd/mm/yyyy, optional HH:MM time."""
    date_str = (date_str or "").strip()
    if not date_str:
        return None
    fmt = "%d/%m/%Y" if len(date_str.split("/")[-1]) == 4 else "%d/%m/%y"
    try:
        dt = datetime.strptime(date_str, fmt)
    except ValueError:
        return None
    time_str = (time_str or "").strip()
    if time_str:
        try:
            t = datetime.strptime(time_str, "%H:%M").time()
            dt = dt.replace(hour=t.hour, minute=t.minute)
        except ValueError:
            pass
    return dt.replace(tzinfo=timezone.utc)


class Command(BaseCommand):
    help = "Ingest historical match stats CSVs from football-data.co.uk."

    def add_arguments(self, parser):
        parser.add_argument("--division", required=True, help="e.g. E0, SP1, I1, D1, F1")
        parser.add_argument(
            "--season",
            nargs="+",
            required=True,
            help="Season code(s) like 2324 (2023/24). Multiple allowed.",
        )

    def handle(self, *args, **options):
        division = options["division"].upper()
        if division not in DIVISIONS:
            raise CommandError(
                f"Unknown division {division}. Known: {', '.join(DIVISIONS)}"
            )
        league = self._get_league(division)

        total = 0
        for season in options["season"]:
            total += self._ingest_season(division, season, league)
        self.stdout.write(
            self.style.SUCCESS(f"Ingested {total} matches with stats into {league.name}.")
        )

    def _get_league(self, division):
        name, country = DIVISIONS[division]
        league, _ = League.objects.update_or_create(
            source=Source.FOOTBALL_DATA,
            external_id=f"fduk-{division}",
            defaults={
                "name": f"{name} (history)",
                "country": country,
                "is_active": False,  # historical training data, hidden from live UI
            },
        )
        return league

    def _team(self, name, league):
        norm = name.strip()
        team, _ = Team.objects.update_or_create(
            source=Source.FOOTBALL_DATA,
            external_id=f"fduk-{slugify(norm)}",
            defaults={"name": norm, "league": league},
        )
        return team

    def _ingest_season(self, division, season, league):
        url = f"{BASE_URL}/{season}/{division}.csv"
        self.stdout.write(f"Fetching {url}")
        text = fetch_csv(url)
        time.sleep(REQUEST_DELAY_SECONDS)  # be polite across many sequential pulls
        if text is None:
            self.stderr.write("  skipped (unavailable)")
            return 0

        # football-data.co.uk CSVs are latin-1 and sometimes have trailing commas.
        reader = csv.DictReader(io.StringIO(text))
        count = 0
        for row in reader:
            if not row.get("HomeTeam") or not row.get("AwayTeam"):
                continue
            if self._ingest_row(row, division, season, league):
                count += 1
        self.stdout.write(f"  {count} matches")
        return count

    def _referee(self, name):
        """The CSVs carry a `Referee` column as an abbreviated name ("A Taylor")."""
        name = (name or "").strip()
        if not name:
            return None
        ref, _ = Referee.objects.get_or_create(
            external_id=f"fduk-{slugify(name)}", defaults={"name": name}
        )
        return ref

    def _ingest_row(self, row, division, season, league):
        kickoff = _parse_date(row.get("Date"), row.get("Time"))
        if kickoff is None:
            return False
        home = self._team(row["HomeTeam"], league)
        away = self._team(row["AwayTeam"], league)
        ext = f"fduk-{division}-{season}-{slugify(row['HomeTeam'])}-{slugify(row['AwayTeam'])}"

        match, _ = Match.objects.update_or_create(
            external_id=ext,
            defaults={
                "league": league,
                "home_team": home,
                "away_team": away,
                "kickoff": kickoff,
                "status": MatchStatus.FINISHED,
                "referee": self._referee(row.get("Referee")),
                "home_score": _to_int(row.get("FTHG")),
                "away_score": _to_int(row.get("FTAG")),
                "raw_data": {k: v for k, v in row.items() if v not in (None, "")},
            },
        )
        MatchStats.objects.update_or_create(
            match=match,
            defaults={
                "home_shots": _to_int(row.get("HS")),
                "away_shots": _to_int(row.get("AS")),
                "home_shots_on_target": _to_int(row.get("HST")),
                "away_shots_on_target": _to_int(row.get("AST")),
                "home_corners": _to_int(row.get("HC")),
                "away_corners": _to_int(row.get("AC")),
                "home_fouls": _to_int(row.get("HF")),
                "away_fouls": _to_int(row.get("AF")),
                "home_yellow_cards": _to_int(row.get("HY")),
                "away_yellow_cards": _to_int(row.get("AY")),
                "home_red_cards": _to_int(row.get("HR")),
                "away_red_cards": _to_int(row.get("AR")),
            },
        )
        return True
