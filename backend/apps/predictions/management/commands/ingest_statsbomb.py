"""Ingest StatsBomb Open Data to seed historical matches + xG for ML training.

    python manage.py ingest_statsbomb --competition 2 --season 27

Pulls match metadata and per-match shot events from the public StatsBomb
open-data GitHub repo, aggregates shot xG per team, and upserts League / Team /
Match / MatchStats rows. This is training data only — not used for live display.
"""
import time
from datetime import datetime, timezone

import requests
from django.core.management.base import BaseCommand, CommandError

from apps.leagues.models import League, Source, Team
from apps.matches.models import Match, MatchStats, MatchStatus

RAW_BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

MAX_RETRIES = 4


def _get(url):
    """GET JSON with retries on transient network errors (timeouts, 5xx, reset)."""
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError:
            raise  # 404 etc. — a real "not found", let the caller decide
        except requests.RequestException as exc:  # timeout / connection reset
            last_exc = exc
            if attempt < MAX_RETRIES:
                time.sleep(attempt * 3)
    raise last_exc


# StatsBomb shot outcomes that count as on-target.
_ON_TARGET = {"Goal", "Saved", "Saved to Post"}


def _apply_card(side, name):
    if name == "Yellow Card":
        side["yellow"] += 1
    elif name == "Second Yellow":
        side["yellow"] += 1
        side["red"] += 1
    elif name == "Red Card":
        side["red"] += 1


def compute_match_stats(events, home_name, away_name):
    """Derive a full per-team stat line from a StatsBomb events list.

    Returns a dict of MatchStats field values: shots, shots-on-target, corners,
    fouls, yellow/red cards, xG, and possession (passes-share proxy). Pure — no
    DB or network — so it is unit-tested directly.
    """
    side_of = {home_name: "home", away_name: "away"}
    agg = {
        s: {"shots": 0, "sot": 0, "corners": 0, "fouls": 0,
            "yellow": 0, "red": 0, "passes": 0, "xg": 0.0}
        for s in ("home", "away")
    }
    for e in events:
        side = side_of.get((e.get("team") or {}).get("name"))
        if side is None:
            continue
        a = agg[side]
        etype = (e.get("type") or {}).get("name")
        if etype == "Shot":
            shot = e.get("shot") or {}
            a["shots"] += 1
            a["xg"] += shot.get("statsbomb_xg") or 0.0
            if (shot.get("outcome") or {}).get("name") in _ON_TARGET:
                a["sot"] += 1
        elif etype == "Pass":
            a["passes"] += 1
            if ((e.get("pass") or {}).get("type") or {}).get("name") == "Corner":
                a["corners"] += 1
        elif etype == "Foul Committed":
            a["fouls"] += 1
            _apply_card(a, ((e.get("foul_committed") or {}).get("card") or {}).get("name"))
        elif etype == "Bad Behaviour":
            _apply_card(a, ((e.get("bad_behaviour") or {}).get("card") or {}).get("name"))

    total_passes = agg["home"]["passes"] + agg["away"]["passes"]

    def possession(side):
        return (
            round(100 * agg[side]["passes"] / total_passes, 1)
            if total_passes
            else None
        )

    return {
        "home_shots": agg["home"]["shots"],
        "away_shots": agg["away"]["shots"],
        "home_shots_on_target": agg["home"]["sot"],
        "away_shots_on_target": agg["away"]["sot"],
        "home_corners": agg["home"]["corners"],
        "away_corners": agg["away"]["corners"],
        "home_fouls": agg["home"]["fouls"],
        "away_fouls": agg["away"]["fouls"],
        "home_yellow_cards": agg["home"]["yellow"],
        "away_yellow_cards": agg["away"]["yellow"],
        "home_red_cards": agg["home"]["red"],
        "away_red_cards": agg["away"]["red"],
        "home_xg": round(agg["home"]["xg"], 3),
        "away_xg": round(agg["away"]["xg"], 3),
        "home_possession": possession("home"),
        "away_possession": possession("away"),
    }


class Command(BaseCommand):
    help = "Ingest StatsBomb open data (matches + xG) for a competition/season."

    def add_arguments(self, parser):
        parser.add_argument("--competition", type=int)
        parser.add_argument("--season", type=int)
        parser.add_argument(
            "--all",
            action="store_true",
            help="Ingest every competition/season in the StatsBomb open-data index.",
        )
        parser.add_argument(
            "--limit", type=int, default=0, help="Cap matches per season (0 = all)."
        )

    def handle(self, *args, **options):
        limit = options["limit"]

        if options["all"]:
            pairs = self._all_competition_seasons()
            self.stdout.write(f"Found {len(pairs)} competition/season pairs.")
        else:
            if options["competition"] is None or options["season"] is None:
                raise CommandError(
                    "Provide --competition and --season, or use --all."
                )
            pairs = [(options["competition"], options["season"])]

        grand_total = 0
        for comp_id, season_id in pairs:
            grand_total += self._ingest_competition_season(comp_id, season_id, limit)
        self.stdout.write(
            self.style.SUCCESS(f"Ingested {grand_total} matches with xG in total.")
        )

    def _all_competition_seasons(self):
        index = _get(f"{RAW_BASE}/competitions.json")
        # Deduplicate (competition_id, season_id) pairs.
        seen = []
        for entry in index:
            pair = (entry["competition_id"], entry["season_id"])
            if pair not in seen:
                seen.append(pair)
        return seen

    def _ingest_competition_season(self, comp_id, season_id, limit):
        matches_url = f"{RAW_BASE}/matches/{comp_id}/{season_id}.json"
        self.stdout.write(f"Fetching {matches_url}")
        try:
            matches = _get(matches_url)
        except requests.HTTPError as exc:
            self.stderr.write(f"  skipped {comp_id}/{season_id}: {exc}")
            return 0
        if limit:
            matches = matches[:limit]

        league = self._get_league(matches[0] if matches else None, comp_id, season_id)
        created = 0
        for sb_match in matches:
            try:
                created += self._ingest_match(sb_match, league)
            except requests.RequestException as exc:
                # Don't let one unreachable events file abort the whole run.
                self.stderr.write(f"  skipping match {sb_match.get('match_id')}: {exc}")
        self.stdout.write(f"  {created} matches")
        return created

    def _get_league(self, sample, comp_id, season_id):
        comp_name = "StatsBomb Competition"
        season_name = str(season_id)
        if sample:
            comp_name = sample.get("competition", {}).get("competition_name", comp_name)
            season_name = sample.get("season", {}).get("season_name", season_name)
        league, _ = League.objects.update_or_create(
            source=Source.FOOTBALL_DATA,
            external_id=f"sb-{comp_id}-{season_id}",
            defaults={
                "name": f"{comp_name} (StatsBomb {season_name})",
                "country": sample.get("competition", {}).get("country_name", "")
                if sample
                else "",
                "season": season_name,
                "is_active": False,  # historical training data, hidden from live UI
            },
        )
        return league

    def _team(self, team_id, team_name, league):
        team, _ = Team.objects.update_or_create(
            source=Source.FOOTBALL_DATA,
            external_id=f"sb-{team_id}",
            defaults={"name": team_name, "league": league},
        )
        return team

    def _ingest_match(self, sb_match, league):
        # Resumable: skip matches that already have the full stat line (we mark
        # completeness by possession, which only the enriched path sets). Older
        # xG-only rows are reprocessed once to backfill the richer stats.
        ext = f"sb-{sb_match['match_id']}"
        if MatchStats.objects.filter(
            match__external_id=ext, home_possession__isnull=False
        ).exists():
            return 0

        # StatsBomb matches.json prefixes keys: home_team_id / home_team_name etc.
        home_obj = sb_match["home_team"]
        away_obj = sb_match["away_team"]
        home = self._team(
            home_obj["home_team_id"], home_obj["home_team_name"], league
        )
        away = self._team(
            away_obj["away_team_id"], away_obj["away_team_name"], league
        )
        kickoff = datetime.fromisoformat(
            f"{sb_match['match_date']}T{sb_match.get('kick_off') or '00:00:00'}"
        ).replace(tzinfo=timezone.utc)

        match, _ = Match.objects.update_or_create(
            external_id=f"sb-{sb_match['match_id']}",
            defaults={
                "league": league,
                "home_team": home,
                "away_team": away,
                "kickoff": kickoff,
                "status": MatchStatus.FINISHED,
                "home_score": sb_match.get("home_score"),
                "away_score": sb_match.get("away_score"),
                "raw_data": sb_match,
            },
        )

        events = _get(f"{RAW_BASE}/events/{sb_match['match_id']}.json")
        stats = compute_match_stats(events, home.name, away.name)
        MatchStats.objects.update_or_create(match=match, defaults=stats)
        return 1
