"""Enrich existing historical matches with Understat data (xG, lineups, goals).

    python manage.py ingest_understat --league EPL --season 2024
    python manage.py ingest_understat --league EPL --season 2024 --details
    python manage.py ingest_understat --all --details

football-data.co.uk gives us shots/corners/fouls/cards but no xG, no possession
and no players. Understat has per-match xG plus a full roster (starting XI,
substitutions, scorers, assists, per-player xG) for the top-5 leagues from
2014/15 onward. This command *merges* that onto the matches already ingested by
``ingest_football_data_uk`` rather than creating a parallel set of rows.

Merge-only by design: this command never creates a League, Team or Match. Every
Understat fixture is resolved against an existing row or skipped and reported,
so re-running it can never duplicate a match or spawn a second copy of a club.
Run ``ingest_football_data_uk`` for the season first.

Understat is an unofficial source; this is for personal/research use.
"""
import codecs
import html
import json
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.leagues.models import League, Player, Source, Team
from apps.matches.models import (
    EventType,
    Match,
    MatchEvent,
    MatchLineup,
    MatchStats,
)

BASE_URL = "https://understat.com"
USER_AGENT = "Mozilla/5.0 (Kickstat data ingest)"

# Be polite: Understat is a small unofficial site and --details is chatty
# (two requests per match).
REQUEST_DELAY_SECONDS = 1.0
MAX_RETRIES = 3

# Understat league code -> the football-data.co.uk division whose "(history)"
# League row holds the matches we are enriching.
LEAGUE_DIVISIONS = {
    "EPL": "E0",
    "La_liga": "SP1",
    "Bundesliga": "D1",
    "Serie_A": "I1",
    "Ligue_1": "F1",
}
SEASONS = list(range(2014, 2026))  # 2014/15 .. 2025/26

# Understat spells clubs out; football-data.co.uk abbreviates. Keyed by the
# normalised Understat name -> normalised football-data.co.uk name. Only pairs
# that normalisation and the prefix fallback cannot bridge need to appear here.
TEAM_ALIASES = {
    # England
    "manchester city": "man city",
    "manchester united": "man united",
    "nottingham forest": "nottm forest",
    "wolverhampton wanderers": "wolves",
    "west bromwich albion": "west brom",
    "queens park rangers": "qpr",
    "sheffield wednesday": "sheffield weds",
    # Spain
    "atletico madrid": "ath madrid",
    "athletic club": "ath bilbao",
    "real sociedad": "sociedad",
    "celta vigo": "celta",
    "deportivo alaves": "alaves",
    "rayo vallecano": "vallecano",
    "real valladolid": "valladolid",
    "espanyol": "espanol",
    # Germany
    "borussia m gladbach": "mgladbach",
    "borussia dortmund": "dortmund",
    "bayer leverkusen": "leverkusen",
    "eintracht frankfurt": "ein frankfurt",
    "vfb stuttgart": "stuttgart",
    "hertha berlin": "hertha",
    "1 fc koln": "fc koln",
    "mainz 05": "mainz",
    # Italy
    "internazionale": "inter",
    "hellas verona": "verona",
    # France
    "paris saint germain": "paris sg",
    "saint etienne": "st etienne",
}

_NOISE_WORDS = re.compile(r"\b(fc|afc|cf|ac|ss|ssc|sc|cd|ud|rcd|as|us|calcio)\b")
_MATCH_INFO_RE = re.compile(r"match_info\s*=\s*JSON\.parse\('([^']+)'\)")


def parse_match_info(html: str) -> dict:
    """Pull the hex-escaped ``match_info`` blob out of a match page."""
    found = _MATCH_INFO_RE.search(html or "")
    if not found:
        return {}
    try:
        return json.loads(codecs.decode(found.group(1), "unicode_escape"))
    except (ValueError, UnicodeDecodeError):
        return {}


def unescape(value):
    """Understat HTML-escapes names — "Matt O&#039;Riley" — so undo that."""
    return html.unescape(value) if isinstance(value, str) else value


def normalise(name: str) -> str:
    """Fold accents, punctuation and club-type noise so names can be compared."""
    folded = unicodedata.normalize("NFKD", unescape(name) or "")
    folded = folded.encode("ascii", "ignore").decode("ascii").lower()
    folded = folded.replace("'", "")  # Nott'm -> nottm, not "nott m"
    folded = re.sub(r"[^a-z0-9 ]", " ", folded)
    folded = _NOISE_WORDS.sub(" ", folded)
    return " ".join(folded.split())


def _to_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value, digits=3):
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


class UnderstatClient:
    """Understat serves its data over XHR endpoints, not in the page HTML.

    Both endpoints 404 without a ``Referer`` and ``X-Requested-With`` header,
    and ``getMatchData`` additionally requires the session cookie handed out by
    the match page itself — so each match costs a page visit plus a data fetch.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

    def _get(self, path, referer, as_json=True):
        headers = {"Referer": f"{BASE_URL}/{referer}", "X-Requested-With": "XMLHttpRequest"}
        last = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(
                    f"{BASE_URL}/{path}", headers=headers, timeout=60
                )
                resp.raise_for_status()
                return resp.json() if as_json else resp.text
            except (requests.RequestException, ValueError) as exc:
                last = exc
                if attempt < MAX_RETRIES:
                    time.sleep(attempt * 3)
        raise last

    def league_data(self, league, season):
        return self._get(
            f"getLeagueData/{league}/{season}", f"league/{league}/{season}"
        )

    def match_data(self, match_id):
        # Prime the session cookie; getMatchData 404s without it. The page also
        # embeds `match_info`, which carries deep completions and PPDA — stats
        # that appear nowhere else, so we parse them out rather than refetch.
        html = self._get(f"match/{match_id}", f"match/{match_id}", as_json=False)
        time.sleep(REQUEST_DELAY_SECONDS)
        return parse_match_info(html), self._get(
            f"getMatchData/{match_id}", f"match/{match_id}"
        )


class Command(BaseCommand):
    help = "Merge Understat xG and lineups into existing historical matches."

    def add_arguments(self, parser):
        parser.add_argument("--league", choices=list(LEAGUE_DIVISIONS))
        parser.add_argument("--season", type=int)
        parser.add_argument("--all", action="store_true")
        parser.add_argument(
            "--details",
            action="store_true",
            help="Also fetch per-match rosters (lineups, goals, assists, cards). Slow.",
        )
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Re-fetch details for matches that already have lineups.",
        )
        parser.add_argument("--limit", type=int, help="Cap matches processed per season.")

    def handle(self, *args, **options):
        if options["all"]:
            pairs = [(lg, yr) for lg in LEAGUE_DIVISIONS for yr in SEASONS]
        elif options["league"] and options["season"]:
            pairs = [(options["league"], options["season"])]
        else:
            raise CommandError("Provide --league and --season, or use --all.")

        self.details = options["details"]
        self.refresh = options["refresh"]
        self.limit = options["limit"]
        self.client = UnderstatClient()

        totals = {"matched": 0, "unmatched": 0, "detailed": 0}
        for league_code, season in pairs:
            result = self._ingest(league_code, season)
            for key in totals:
                totals[key] += result[key]

        self.stdout.write(
            self.style.SUCCESS(
                f"Enriched {totals['matched']} matches "
                f"({totals['detailed']} with lineups); "
                f"{totals['unmatched']} unmatched."
            )
        )

    # ------------------------------------------------------------------ setup

    def _history_league(self, league_code):
        """The '(history)' League row holding this competition's matches."""
        try:
            return League.objects.get(
                source=Source.FOOTBALL_DATA,
                external_id=f"fduk-{LEAGUE_DIVISIONS[league_code]}",
            )
        except League.DoesNotExist:
            return None

    def _team_index(self, league):
        """Map every normalised spelling of this league's teams to its Team row.

        Indexed by the teams that actually appear in this league's matches, not
        by ``Team.league``: football-data.co.uk keys clubs on name alone, so a
        club that has played in two divisions (Ipswich in E0 and E1) ends up
        with its ``league`` pointing at whichever was ingested last.
        """
        matches = Match.objects.filter(league=league)
        team_ids = set(
            matches.values_list("home_team_id", flat=True).distinct()
        ) | set(matches.values_list("away_team_id", flat=True).distinct())
        index = {}
        for team in Team.objects.filter(id__in=team_ids):
            index.setdefault(normalise(team.name), team)
            if team.short_name:
                index.setdefault(normalise(team.short_name), team)
        return index

    def _resolve_team(self, title, index):
        key = normalise(title)
        if key in index:
            return index[key]
        aliased = TEAM_ALIASES.get(key)
        if aliased and aliased in index:
            return index[aliased]
        # Fall back to a prefix match ("Newcastle United" -> "Newcastle"), but
        # only when exactly one team qualifies, so we never guess.
        hits = [t for k, t in index.items() if key.startswith(k) or k.startswith(key)]
        unique = {t.id: t for t in hits}
        if len(unique) == 1:
            return next(iter(unique.values()))
        return None

    # -------------------------------------------------------------- ingestion

    def _ingest(self, league_code, season):
        empty = {"matched": 0, "unmatched": 0, "detailed": 0}
        league = self._history_league(league_code)
        if league is None:
            self.stderr.write(
                f"  no '(history)' league for {league_code} — "
                f"run ingest_football_data_uk first"
            )
            return empty

        self.stdout.write(f"Understat {league_code} {season}")
        try:
            data = self.client.league_data(league_code, season)
        except (requests.RequestException, ValueError) as exc:
            self.stderr.write(f"  skipped: {exc}")
            return empty
        time.sleep(REQUEST_DELAY_SECONDS)

        index = self._team_index(league)
        played = [e for e in data.get("dates", []) if e.get("isResult")]
        if self.limit:
            played = played[: self.limit]

        counts = dict(empty)
        unresolved_teams, unmatched_fixtures = set(), []
        for entry in played:
            match = self._find_match(entry, league, index, unresolved_teams)
            if match is None:
                counts["unmatched"] += 1
                unmatched_fixtures.append(
                    f"{entry['datetime'][:10]} {entry['h']['title']} v {entry['a']['title']}"
                )
                continue
            self._merge_stats(match, entry)
            counts["matched"] += 1
            if self.details:
                counts["detailed"] += self._merge_details(match, entry["id"])

        self.stdout.write(
            f"  {counts['matched']} enriched, {counts['detailed']} with lineups"
        )
        if unresolved_teams:
            self.stderr.write(f"  unresolved teams: {', '.join(sorted(unresolved_teams))}")
        for line in unmatched_fixtures[:10]:
            self.stderr.write(f"  no local match: {line}")
        if len(unmatched_fixtures) > 10:
            self.stderr.write(f"  ...and {len(unmatched_fixtures) - 10} more")
        return counts

    def _find_match(self, entry, league, index, unresolved):
        """Resolve an Understat fixture to exactly one existing Match, or None."""
        home = self._resolve_team(entry["h"]["title"], index)
        away = self._resolve_team(entry["a"]["title"], index)
        for title, team in ((entry["h"]["title"], home), (entry["a"]["title"], away)):
            if team is None:
                unresolved.add(title)
        if home is None or away is None:
            return None

        kickoff = datetime.strptime(entry["datetime"], "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
        # Kickoff times differ by source (and by timezone at the edges), so key
        # on the fixture itself and allow a day either side.
        matches = list(
            Match.objects.filter(
                league=league,
                home_team=home,
                away_team=away,
                kickoff__gte=kickoff - timedelta(days=1),
                kickoff__lte=kickoff + timedelta(days=1),
            )
        )
        if len(matches) != 1:
            return None
        return matches[0]

    def _merge_stats(self, match, entry):
        stats, _ = MatchStats.objects.get_or_create(match=match)
        stats.home_xg = _to_float(entry.get("xG", {}).get("h"))
        stats.away_xg = _to_float(entry.get("xG", {}).get("a"))
        stats.save(update_fields=["home_xg", "away_xg", "updated_at"])

        # Keep the source fixture id so re-runs are traceable and idempotent.
        raw = match.raw_data if isinstance(match.raw_data, dict) else {}
        raw["understat"] = {"id": entry["id"], "forecast": entry.get("forecast")}
        match.raw_data = raw
        match.save(update_fields=["raw_data", "updated_at"])

    def _merge_details(self, match, understat_id):
        if not self.refresh and match.lineups.exists():
            return 0
        try:
            data = self.client.match_data(understat_id)
        except (requests.RequestException, ValueError) as exc:
            self.stderr.write(f"  match {understat_id}: {exc}")
            return 0
        time.sleep(REQUEST_DELAY_SECONDS)

        info, data = data
        rosters = data.get("rosters") or {}
        if not rosters.get("h") or not rosters.get("a"):
            return 0

        sides = {"h": match.home_team, "a": match.away_team}
        with transaction.atomic():
            players, subs = self._store_lineups(match, rosters, sides)
            self._store_timeline(match, data, rosters, sides, players, subs)
            self._merge_extra_stats(match, info)
        return 1

    def _merge_extra_stats(self, match, info):
        """Fold deep completions and PPDA into ``MatchStats.extra``."""
        if not info:
            return
        stats, _ = MatchStats.objects.get_or_create(match=match)
        extra = stats.extra if isinstance(stats.extra, dict) else {}
        for side, key in (("h", "home"), ("a", "away")):
            side_extra = dict(extra.get(key) or {})
            deep = _to_int(info.get(f"{side}_deep"))
            ppda = _to_float(info.get(f"{side}_ppda"), 2)
            if deep is not None:
                side_extra["deep_completions"] = deep
            if ppda is not None:
                side_extra["ppda"] = ppda
            extra[key] = side_extra
        stats.extra = extra
        stats.save(update_fields=["extra", "updated_at"])

    # ------------------------------------------------------------ persistence

    def _player(self, understat_id, name, team):
        if not understat_id or not name:
            return None
        player, _ = Player.objects.update_or_create(
            external_id=f"us-{understat_id}",
            defaults={"name": unescape(name), "team": team},
        )
        return player

    def _store_lineups(self, match, rosters, sides):
        """Rebuild this match's lineups.

        Understat reports minutes played rather than substitution minutes, but
        it links each pairing: a starter's ``roster_in`` is the roster row of
        the player who replaced them, and a sub's ``roster_out`` is the starter
        they came on for. So a starter leaves at their own ``time``, and their
        replacement enters at that same minute.

        Returns ``({understat player id: Player}, [(team, minute, off, on)])``.
        """
        match.lineups.all().delete()

        by_roster_id = {}
        for entries in rosters.values():
            for row in entries.values():
                by_roster_id[str(row.get("id"))] = row

        rows, players, by_roster_player, subs = [], {}, {}, []
        for side, entries in rosters.items():
            team = sides.get(side)
            if team is None:
                continue
            for row in entries.values():
                player = self._player(row.get("player_id"), row.get("player"), team)
                if player is None:
                    continue
                players[str(row.get("player_id"))] = player
                by_roster_player[str(row.get("id"))] = player

                position = row.get("position") or ""
                is_starter = position != "Sub"
                minutes = _to_int(row.get("time"))
                on_min = off_min = None
                if is_starter and _to_int(row.get("roster_in")):
                    off_min = minutes  # replaced after playing `time` minutes
                elif not is_starter:
                    replaced = by_roster_id.get(str(row.get("roster_out")))
                    on_min = _to_int(replaced.get("time")) if replaced else None
                rows.append(
                    MatchLineup(
                        match=match,
                        team=team,
                        player=player,
                        position=position,
                        is_starter=is_starter,
                        subbed_on_minute=on_min,
                        subbed_off_minute=off_min,
                    )
                )
        MatchLineup.objects.bulk_create(rows)

        # Second pass: both halves of each pairing now have a Player row.
        for side, entries in rosters.items():
            team = sides.get(side)
            if team is None:
                continue
            for row in entries.values():
                if (row.get("position") or "") != "Sub":
                    continue
                replaced = by_roster_id.get(str(row.get("roster_out")))
                on = by_roster_player.get(str(row.get("id")))
                off = by_roster_player.get(str(row.get("roster_out")))
                if replaced is None or on is None:
                    continue
                subs.append((team, _to_int(replaced.get("time")), off, on))
        return players, subs

    def _store_timeline(self, match, data, rosters, sides, players, subs):
        """Rebuild goals, assists, cards and substitutions from the shot map."""
        match.events.all().delete()

        by_name = {}
        for side, entries in rosters.items():
            for row in entries.values():
                player = players.get(str(row.get("player_id")))
                if player is not None:
                    by_name[unescape(row.get("player"))] = player

        rows = []
        for side, shots in (data.get("shots") or {}).items():
            team = sides.get(side)
            if team is None:
                continue
            for shot in shots:
                result = shot.get("result")
                if result not in ("Goal", "OwnGoal"):
                    continue
                scorer = by_name.get(unescape(shot.get("player")))
                assist = by_name.get(unescape(shot.get("player_assisted")))
                is_own = result == "OwnGoal"
                rows.append(
                    MatchEvent(
                        match=match,
                        minute=_to_int(shot.get("minute")),
                        # Own goals are logged against the team that scored
                        # them, matching the StatsBomb ingest's convention.
                        type=EventType.OWN_GOAL if is_own else EventType.GOAL,
                        team=team,
                        player=scorer,
                        assist=None if is_own else assist,
                        detail={
                            "own_goal": is_own,
                            "penalty": shot.get("situation") == "Penalty",
                            "body_part": shot.get("shotType"),
                            "xg": _to_float(shot.get("xG")),
                        },
                    )
                )

        for side, entries in rosters.items():
            team = sides.get(side)
            if team is None:
                continue
            for row in entries.values():
                player = players.get(str(row.get("player_id")))
                if player is None:
                    continue
                # Understat reports card counts without minutes, so these land
                # on the timeline unminuted rather than at a guessed position.
                for count, kind in (
                    (_to_int(row.get("yellow_card")), EventType.YELLOW),
                    (_to_int(row.get("red_card")), EventType.RED),
                ):
                    for _ in range(count or 0):
                        rows.append(
                            MatchEvent(
                                match=match, type=kind, team=team, player=player
                            )
                        )

        for team, minute, off, on in subs:
            rows.append(
                MatchEvent(
                    match=match,
                    minute=minute,
                    type=EventType.SUBSTITUTION,
                    team=team,
                    player=off,  # going off
                    assist=on,  # coming on
                )
            )
        MatchEvent.objects.bulk_create(rows)
