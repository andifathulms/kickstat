import json
from datetime import datetime, timezone
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from apps.leagues.models import League, Player, Source, Team
from apps.matches.models import (
    EventType,
    Match,
    MatchEvent,
    MatchLineup,
    MatchStats,
    MatchStatus,
)
from apps.sync.management.commands import ingest_understat as cmd

ENTRIES = [
    {
        "id": "1001",
        "isResult": True,
        "h": {"id": "88", "title": "Manchester City", "short_title": "MCI"},
        "a": {"id": "89", "title": "Newcastle United", "short_title": "NEW"},
        "goals": {"h": "1", "a": "1"},
        "xG": {"h": "2.41", "a": "0.77"},
        "datetime": "2023-10-29 15:30:00",
    },
    {
        "id": "1002",
        "isResult": False,  # upcoming -> skipped
        "h": {"id": "88", "title": "Manchester City", "short_title": "MCI"},
        "a": {"id": "90", "title": "Arsenal", "short_title": "ARS"},
        "goals": {"h": "0", "a": "0"},
        "xG": {"h": "0", "a": "0"},
        "datetime": "2099-01-01 15:30:00",
    },
]

ROSTERS = {
    "h": {
        "1": {
            "id": "1", "player_id": "10", "player": "Erling Haaland",
            "position": "FW", "time": "70", "roster_in": "3", "roster_out": "0",
            "goals": "1", "assists": "0", "yellow_card": "0", "red_card": "0",
        },
        "2": {
            "id": "2", "player_id": "11", "player": "Rodri",
            "position": "MC", "time": "90", "roster_in": "0", "roster_out": "0",
            "goals": "0", "assists": "1", "yellow_card": "0", "red_card": "0",
        },
        "3": {
            "id": "3", "player_id": "12", "player": "Julián Álvarez",
            "position": "Sub", "time": "20", "roster_in": "0", "roster_out": "1",
            "goals": "0", "assists": "0", "yellow_card": "0", "red_card": "0",
        },
    },
    "a": {
        # Understat HTML-escapes apostrophes.
        "4": {
            "id": "4", "player_id": "20", "player": "Matt O&#039;Riley",
            "position": "MC", "time": "90", "roster_in": "0", "roster_out": "0",
            "goals": "0", "assists": "0", "yellow_card": "1", "red_card": "0",
        },
    },
}

SHOTS = {
    "h": [
        {
            "minute": "30", "result": "Goal", "player": "Erling Haaland",
            "player_assisted": "Rodri", "xG": "0.4123", "situation": "OpenPlay",
            "shotType": "LeftFoot",
        },
        {"minute": "55", "result": "MissedShots", "player": "Rodri", "xG": "0.05"},
    ],
    "a": [
        {
            "minute": "80", "result": "OwnGoal", "player": "Matt O&#039;Riley",
            "player_assisted": None, "xG": "0", "situation": "OpenPlay",
        },
    ],
}

MATCH_INFO = {"h_deep": "12", "a_deep": "4", "h_ppda": "8.53", "a_ppda": "20.19"}


class FakeClient:
    """Stands in for UnderstatClient so tests never touch the network."""

    def __init__(self, entries=ENTRIES):
        self.entries = entries
        self.match_calls = []

    def league_data(self, league, season):
        return {"dates": self.entries, "teams": {}, "players": {}}

    def match_data(self, match_id):
        self.match_calls.append(match_id)
        return MATCH_INFO, {"rosters": ROSTERS, "shots": SHOTS}


def run(*args, client=None):
    client = client or FakeClient()
    with mock.patch.object(cmd, "UnderstatClient", return_value=client), \
            mock.patch.object(cmd.time, "sleep"):
        call_command("ingest_understat", *args)
    return client


class NormaliseTests(TestCase):
    def test_folds_accents_punctuation_and_club_noise(self):
        self.assertEqual(cmd.normalise("Nott'm Forest"), "nottm forest")
        self.assertEqual(cmd.normalise("Atlético Madrid"), "atletico madrid")
        self.assertEqual(cmd.normalise("Brighton FC"), "brighton")

    def test_parse_match_info(self):
        blob = json.dumps(MATCH_INFO)
        escaped = "".join("\\x%02x" % b for b in blob.encode("utf-8"))
        html = f"<script>var match_info = JSON.parse('{escaped}');</script>"
        self.assertEqual(cmd.parse_match_info(html), MATCH_INFO)

    def test_parse_match_info_missing_blob(self):
        self.assertEqual(cmd.parse_match_info("<html></html>"), {})


class MergeBaseTestCase(TestCase):
    def setUp(self):
        self.league = League.objects.create(
            source=Source.FOOTBALL_DATA,
            external_id="fduk-E0",
            name="Premier League (history)",
            country="England",
            is_active=False,
        )
        # football-data.co.uk spellings, which differ from Understat's.
        self.city = Team.objects.create(
            source=Source.FOOTBALL_DATA, external_id="fduk-man-city",
            name="Man City", league=self.league,
        )
        self.newcastle = Team.objects.create(
            source=Source.FOOTBALL_DATA, external_id="fduk-newcastle",
            name="Newcastle", league=self.league,
        )
        self.match = Match.objects.create(
            external_id="fduk-E0-2324-man-city-newcastle",
            league=self.league,
            home_team=self.city,
            away_team=self.newcastle,
            # Understat's kickoff time differs from the CSV's; the match must
            # still resolve.
            kickoff=datetime(2023, 10, 29, 14, 0, tzinfo=timezone.utc),
            status=MatchStatus.FINISHED,
            home_score=1,
            away_score=1,
        )


class MergeStatsTests(MergeBaseTestCase):
    def test_merges_xg_onto_existing_match(self):
        run("--league", "EPL", "--season", "2023")
        stats = MatchStats.objects.get(match=self.match)
        self.assertEqual(stats.home_xg, 2.41)
        self.assertEqual(stats.away_xg, 0.77)
        self.match.refresh_from_db()
        self.assertEqual(self.match.raw_data["understat"]["id"], "1001")

    def test_creates_no_leagues_teams_or_matches(self):
        run("--league", "EPL", "--season", "2023")
        self.assertEqual(League.objects.count(), 1)
        self.assertEqual(Team.objects.count(), 2)
        self.assertEqual(Match.objects.count(), 1)

    def test_idempotent_across_reruns(self):
        run("--league", "EPL", "--season", "2023")
        run("--league", "EPL", "--season", "2023", "--details")
        run("--league", "EPL", "--season", "2023", "--details")
        self.assertEqual(Match.objects.count(), 1)
        self.assertEqual(MatchStats.objects.count(), 1)
        self.assertEqual(MatchLineup.objects.filter(match=self.match).count(), 4)
        self.assertEqual(Player.objects.count(), 4)

    def test_details_skipped_when_lineups_exist_unless_refresh(self):
        client = run("--league", "EPL", "--season", "2023", "--details")
        self.assertEqual(client.match_calls, ["1001"])

        again = run("--league", "EPL", "--season", "2023", "--details")
        self.assertEqual(again.match_calls, [])  # already has lineups

        forced = run("--league", "EPL", "--season", "2023", "--details", "--refresh")
        self.assertEqual(forced.match_calls, ["1001"])


class MatchResolutionTests(MergeBaseTestCase):
    def test_unknown_fixture_is_skipped_not_created(self):
        entries = [dict(ENTRIES[0], h={"id": "9", "title": "Luton", "short_title": "LUT"})]
        run("--league", "EPL", "--season", "2023", client=FakeClient(entries))
        self.assertEqual(Match.objects.count(), 1)
        self.assertIsNone(MatchStats.objects.filter(match=self.match).first())

    def test_ambiguous_window_is_skipped(self):
        # A second same-fixture row inside the ±1 day window makes the merge
        # target ambiguous; skipping beats guessing.
        Match.objects.create(
            external_id="dupe",
            league=self.league,
            home_team=self.city,
            away_team=self.newcastle,
            kickoff=datetime(2023, 10, 29, 18, 0, tzinfo=timezone.utc),
            status=MatchStatus.FINISHED,
        )
        run("--league", "EPL", "--season", "2023")
        self.assertEqual(MatchStats.objects.count(), 0)

    def test_resolves_teams_whose_league_points_elsewhere(self):
        # football-data.co.uk keys clubs on name alone, so a club that has also
        # played in another division carries that division's league FK. It must
        # still resolve via the matches it appears in.
        other = League.objects.create(
            source=Source.FOOTBALL_DATA,
            external_id="fduk-E1",
            name="Championship (history)",
            country="England",
        )
        self.newcastle.league = other
        self.newcastle.save(update_fields=["league"])

        run("--league", "EPL", "--season", "2023")
        self.assertEqual(MatchStats.objects.get(match=self.match).home_xg, 2.41)

    def test_missing_history_league_is_reported_not_created(self):
        League.objects.all().delete()
        run("--league", "EPL", "--season", "2023")
        self.assertEqual(League.objects.count(), 0)


class MergeDetailsTests(MergeBaseTestCase):
    def setUp(self):
        super().setUp()
        run("--league", "EPL", "--season", "2023", "--details")

    def test_lineups_split_starters_from_subs(self):
        lineups = {l.player.name: l for l in MatchLineup.objects.filter(match=self.match)}
        self.assertEqual(len(lineups), 4)
        self.assertTrue(lineups["Erling Haaland"].is_starter)
        self.assertFalse(lineups["Julián Álvarez"].is_starter)
        self.assertEqual(lineups["Erling Haaland"].team, self.city)
        self.assertEqual(lineups["Matt O'Riley"].team, self.newcastle)

    def test_substitution_minutes_come_from_the_pairing(self):
        off = MatchLineup.objects.get(match=self.match, player__name="Erling Haaland")
        on = MatchLineup.objects.get(match=self.match, player__name="Julián Álvarez")
        self.assertEqual(off.subbed_off_minute, 70)
        self.assertEqual(on.subbed_on_minute, 70)

        event = MatchEvent.objects.get(match=self.match, type=EventType.SUBSTITUTION)
        self.assertEqual(event.minute, 70)
        self.assertEqual(event.player.name, "Erling Haaland")  # going off
        self.assertEqual(event.assist.name, "Julián Álvarez")  # coming on

    def test_goal_carries_scorer_assist_and_xg(self):
        goal = MatchEvent.objects.get(match=self.match, type=EventType.GOAL)
        self.assertEqual(goal.minute, 30)
        self.assertEqual(goal.player.name, "Erling Haaland")
        self.assertEqual(goal.assist.name, "Rodri")
        self.assertEqual(goal.team, self.city)
        self.assertEqual(goal.detail["xg"], 0.412)

    def test_own_goal_logged_against_the_scoring_player(self):
        own = MatchEvent.objects.get(match=self.match, type=EventType.OWN_GOAL)
        self.assertEqual(own.minute, 80)
        self.assertEqual(own.player.name, "Matt O'Riley")
        self.assertEqual(own.team, self.newcastle)
        self.assertIsNone(own.assist)

    def test_non_goal_shots_do_not_become_events(self):
        self.assertEqual(MatchEvent.objects.filter(match=self.match).count(), 4)

    def test_cards_recorded_without_a_minute(self):
        card = MatchEvent.objects.get(match=self.match, type=EventType.YELLOW)
        self.assertEqual(card.player.name, "Matt O'Riley")
        self.assertIsNone(card.minute)

    def test_deep_and_ppda_land_in_extra(self):
        stats = MatchStats.objects.get(match=self.match)
        self.assertEqual(stats.extra["home"]["deep_completions"], 12)
        self.assertEqual(stats.extra["away"]["ppda"], 20.19)
