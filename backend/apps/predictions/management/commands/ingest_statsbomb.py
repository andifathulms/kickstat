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

from apps.leagues.models import League, Player, Source, Team
from apps.matches.models import (
    EventType,
    Match,
    MatchEvent,
    MatchLineup,
    MatchStats,
    MatchStatus,
)

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

    Returns a dict of MatchStats field values plus an ``extra`` dict carrying the
    long tail of metrics (passes, pass accuracy, crosses, throw-ins, offsides,
    tackles, interceptions, blocks, clearances, dribbles, recoveries, duels,
    saves, …) so nothing is dropped. Pure — no DB or network.
    """
    side_of = {home_name: "home", away_name: "away"}

    def new_side():
        return {
            "shots": 0, "sot": 0, "corners": 0, "fouls": 0, "yellow": 0,
            "red": 0, "passes": 0, "xg": 0.0,
            # extended
            "passes_completed": 0, "crosses": 0, "throw_ins": 0, "free_kicks": 0,
            "offsides": 0, "interceptions": 0, "blocks": 0, "clearances": 0,
            "dribbles": 0, "dribbles_completed": 0, "ball_recoveries": 0,
            "duels": 0, "duels_won": 0, "dispossessed": 0, "fouls_won": 0,
            "saves": 0, "pressures": 0,
        }

    agg = {"home": new_side(), "away": new_side()}

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
            p = e.get("pass") or {}
            a["passes"] += 1
            if not p.get("outcome"):  # no outcome => completed
                a["passes_completed"] += 1
            ptype = (p.get("type") or {}).get("name")
            if ptype == "Corner":
                a["corners"] += 1
            elif ptype == "Throw-in":
                a["throw_ins"] += 1
            elif ptype == "Free Kick":
                a["free_kicks"] += 1
            if p.get("cross"):
                a["crosses"] += 1
        elif etype == "Foul Committed":
            a["fouls"] += 1
            _apply_card(a, ((e.get("foul_committed") or {}).get("card") or {}).get("name"))
        elif etype == "Bad Behaviour":
            _apply_card(a, ((e.get("bad_behaviour") or {}).get("card") or {}).get("name"))
        elif etype == "Foul Won":
            a["fouls_won"] += 1
        elif etype == "Offside":
            a["offsides"] += 1
        elif etype == "Interception":
            a["interceptions"] += 1
        elif etype == "Block":
            a["blocks"] += 1
        elif etype == "Clearance":
            a["clearances"] += 1
        elif etype == "Ball Recovery":
            a["ball_recoveries"] += 1
        elif etype == "Dispossessed":
            a["dispossessed"] += 1
        elif etype == "Pressure":
            a["pressures"] += 1
        elif etype == "Dribble":
            a["dribbles"] += 1
            if ((e.get("dribble") or {}).get("outcome") or {}).get("name") == "Complete":
                a["dribbles_completed"] += 1
        elif etype == "Duel":
            a["duels"] += 1
            if ((e.get("duel") or {}).get("outcome") or {}).get("name") in (
                "Won", "Success", "Success In Play", "Success Out",
            ):
                a["duels_won"] += 1
        elif etype == "Goal Keeper":
            gk = ((e.get("goalkeeper") or {}).get("type") or {}).get("name")
            if gk in ("Shot Saved", "Save", "Saved to Post", "Penalty Saved"):
                a["saves"] += 1

    total_passes = agg["home"]["passes"] + agg["away"]["passes"]

    def possession(side):
        return (
            round(100 * agg[side]["passes"] / total_passes, 1)
            if total_passes
            else None
        )

    def extra(side):
        a = agg[side]
        acc = (
            round(100 * a["passes_completed"] / a["passes"], 1)
            if a["passes"]
            else None
        )
        return {
            "passes": a["passes"],
            "passes_completed": a["passes_completed"],
            "pass_accuracy": acc,
            "crosses": a["crosses"],
            "throw_ins": a["throw_ins"],
            "free_kicks": a["free_kicks"],
            "offsides": a["offsides"],
            "interceptions": a["interceptions"],
            "blocks": a["blocks"],
            "clearances": a["clearances"],
            "dribbles": a["dribbles"],
            "dribbles_completed": a["dribbles_completed"],
            "ball_recoveries": a["ball_recoveries"],
            "duels": a["duels"],
            "duels_won": a["duels_won"],
            "dispossessed": a["dispossessed"],
            "fouls_won": a["fouls_won"],
            "saves": a["saves"],
            "pressures": a["pressures"],
        }

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
        "extra": {"home": extra("home"), "away": extra("away")},
    }


def _minute(value) -> int | None:
    """Parse a StatsBomb minute: int passthrough or 'MM:SS' -> MM."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value).split(":")[0])
    except (ValueError, IndexError):
        return None


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
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Reprocess matches even if already enriched (lineups present).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        self.refresh = options["refresh"]

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

    def _player(self, player_id, name, team, nickname="", nationality="", position=""):
        if not player_id:
            return None
        player, _ = Player.objects.update_or_create(
            external_id=f"sb-{player_id}",
            defaults={
                "name": name or "",
                "nickname": nickname or "",
                "nationality": nationality or "",
                "position": position or "",
                "team": team,
            },
        )
        return player

    def _ingest_match(self, sb_match, league):
        ext = f"sb-{sb_match['match_id']}"
        # Resumable: skip matches already enriched (lineups present) unless
        # --refresh. The old completeness marker was possession-only.
        if not self.refresh and MatchLineup.objects.filter(
            match__external_id=ext
        ).exists():
            return 0

        match_id = sb_match["match_id"]
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

        def manager(team_obj):
            managers = team_obj.get("managers") or []
            return managers[0]["name"] if managers else ""

        match, _ = Match.objects.update_or_create(
            external_id=ext,
            defaults={
                "league": league,
                "home_team": home,
                "away_team": away,
                "kickoff": kickoff,
                "matchday": sb_match.get("match_week"),
                "status": MatchStatus.FINISHED,
                "home_score": sb_match.get("home_score"),
                "away_score": sb_match.get("away_score"),
                "referee": (sb_match.get("referee") or {}).get("name", ""),
                "stadium": (sb_match.get("stadium") or {}).get("name", ""),
                "home_manager": manager(home_obj),
                "away_manager": manager(away_obj),
                "raw_data": sb_match,
            },
        )

        events = _get(f"{RAW_BASE}/events/{match_id}.json")
        stats = compute_match_stats(events, home.name, away.name)
        MatchStats.objects.update_or_create(match=match, defaults=stats)

        # Lineups + timeline are rebuilt from scratch each run (no natural key).
        team_by_name = {home.name: home, away.name: away}
        match.lineups.all().delete()
        match.events.all().delete()
        try:
            lineups = _get(f"{RAW_BASE}/lineups/{match_id}.json")
            self._store_lineups(match, lineups, team_by_name)
        except requests.HTTPError:
            lineups = []
        self._store_timeline(match, events, team_by_name)
        return 1

    def _store_lineups(self, match, lineups, team_by_name):
        rows = []
        for team_block in lineups:
            team = team_by_name.get(team_block.get("team_name"))
            if team is None:
                continue
            for p in team_block.get("lineup", []):
                positions = p.get("positions") or []
                first = positions[0] if positions else {}
                is_starter = first.get("start_reason") == "Starting XI"
                on_min = off_min = None
                for pos in positions:
                    if str(pos.get("start_reason", "")).startswith("Substitution"):
                        on_min = _minute(pos.get("from"))
                    if str(pos.get("end_reason", "")).startswith("Substitution"):
                        off_min = _minute(pos.get("to"))
                player = self._player(
                    p.get("player_id"),
                    p.get("player_name"),
                    team,
                    nickname=p.get("player_nickname") or "",
                    nationality=(p.get("country") or {}).get("name", ""),
                    position=first.get("position", ""),
                )
                if player is None:
                    continue
                rows.append(
                    MatchLineup(
                        match=match,
                        team=team,
                        player=player,
                        shirt_number=p.get("jersey_number"),
                        position=first.get("position", ""),
                        is_starter=is_starter,
                        subbed_on_minute=on_min,
                        subbed_off_minute=off_min,
                    )
                )
        MatchLineup.objects.bulk_create(rows)

    def _store_timeline(self, match, events, team_by_name):
        by_id = {e.get("id"): e for e in events}
        rows = []

        def team_of(e):
            return team_by_name.get((e.get("team") or {}).get("name"))

        def player_of(e, team):
            pl = e.get("player") or {}
            return self._player(pl.get("id"), pl.get("name"), team)

        for e in events:
            etype = (e.get("type") or {}).get("name")
            team = team_of(e)

            if etype == "Shot":
                shot = e.get("shot") or {}
                if (shot.get("outcome") or {}).get("name") != "Goal":
                    continue
                scorer = player_of(e, team)
                assist = None
                kp = shot.get("key_pass_id")
                if kp and kp in by_id:
                    kp_ev = by_id[kp]
                    assist = self._player(
                        (kp_ev.get("player") or {}).get("id"),
                        (kp_ev.get("player") or {}).get("name"),
                        team_of(kp_ev),
                    )
                rows.append(
                    MatchEvent(
                        match=match,
                        minute=_minute(e.get("minute")),
                        type=EventType.GOAL,
                        team=team,
                        player=scorer,
                        assist=assist,
                        detail={
                            "penalty": (shot.get("type") or {}).get("name") == "Penalty",
                            "body_part": (shot.get("body_part") or {}).get("name"),
                            "xg": round(shot.get("statsbomb_xg") or 0.0, 3),
                        },
                    )
                )
            elif etype == "Own Goal Against":
                rows.append(
                    MatchEvent(
                        match=match,
                        minute=_minute(e.get("minute")),
                        type=EventType.OWN_GOAL,
                        team=team,
                        player=player_of(e, team),
                        detail={"own_goal": True},
                    )
                )
            elif etype == "Substitution":
                off = player_of(e, team)
                repl = (e.get("substitution") or {}).get("replacement") or {}
                on = self._player(repl.get("id"), repl.get("name"), team)
                rows.append(
                    MatchEvent(
                        match=match,
                        minute=_minute(e.get("minute")),
                        type=EventType.SUBSTITUTION,
                        team=team,
                        player=off,
                        assist=on,  # reuse: player coming on
                        detail={
                            "player_off": (off.name if off else None),
                            "player_on": (on.name if on else None),
                        },
                    )
                )
            elif etype in ("Foul Committed", "Bad Behaviour"):
                key = "foul_committed" if etype == "Foul Committed" else "bad_behaviour"
                card = ((e.get(key) or {}).get("card") or {}).get("name")
                if not card:
                    continue
                second_yellow = card == "Second Yellow"
                card_type = EventType.YELLOW if card == "Yellow Card" else EventType.RED
                rows.append(
                    MatchEvent(
                        match=match,
                        minute=_minute(e.get("minute")),
                        type=card_type,
                        team=team,
                        player=player_of(e, team),
                        detail={"card": card, "second_yellow": second_yellow},
                    )
                )

        MatchEvent.objects.bulk_create([r for r in rows if r is not None])
