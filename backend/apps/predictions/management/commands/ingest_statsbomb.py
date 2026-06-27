"""Ingest StatsBomb Open Data to seed historical matches + xG for ML training.

    python manage.py ingest_statsbomb --competition 2 --season 27

Pulls match metadata and per-match shot events from the public StatsBomb
open-data GitHub repo, aggregates shot xG per team, and upserts League / Team /
Match / MatchStats rows. This is training data only — not used for live display.
"""
from datetime import datetime, timezone

import requests
from django.core.management.base import BaseCommand, CommandError

from apps.leagues.models import League, Source, Team
from apps.matches.models import Match, MatchStats, MatchStatus

RAW_BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"


def _get(url):
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


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
            except requests.HTTPError as exc:
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

        home_xg, away_xg = self._aggregate_xg(sb_match["match_id"], home, away)
        MatchStats.objects.update_or_create(
            match=match,
            defaults={"home_xg": round(home_xg, 3), "away_xg": round(away_xg, 3)},
        )
        return 1

    def _aggregate_xg(self, match_id, home, away):
        events = _get(f"{RAW_BASE}/events/{match_id}.json")
        home_xg = away_xg = 0.0
        for event in events:
            if event.get("type", {}).get("name") != "Shot":
                continue
            xg = event.get("shot", {}).get("statsbomb_xg", 0.0)
            team_name = event.get("team", {}).get("name")
            if team_name == home.name:
                home_xg += xg
            elif team_name == away.name:
                away_xg += xg
        return home_xg, away_xg
