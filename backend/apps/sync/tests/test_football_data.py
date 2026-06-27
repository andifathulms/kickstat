from unittest import mock

from django.test import TestCase

from apps.common.test_factories import make_league
from apps.leagues.models import League, Standing, Team
from apps.matches.models import Match, MatchStatus
from apps.sync.models import SyncLog
from apps.sync.tasks import football_data as fd

STANDINGS_RESPONSE = {
    "season": {"startDate": "2025-08-01"},
    "standings": [
        {
            "type": "TOTAL",
            "table": [
                {
                    "position": 1,
                    "team": {"id": 57, "name": "Arsenal FC", "tla": "ARS", "crest": "http://x/ars.png"},
                    "playedGames": 10, "won": 8, "draw": 1, "lost": 1,
                    "goalsFor": 24, "goalsAgainst": 8, "goalDifference": 16, "points": 25,
                },
                {
                    "position": 2,
                    "team": {"id": 61, "name": "Chelsea FC", "tla": "CHE", "crest": "http://x/che.png"},
                    "playedGames": 10, "won": 7, "draw": 2, "lost": 1,
                    "goalsFor": 20, "goalsAgainst": 10, "goalDifference": 10, "points": 23,
                },
            ],
        },
        {"type": "HOME", "table": []},  # should be ignored
    ],
}

MATCHES_RESPONSE = {
    "matches": [
        {
            "id": 1001,
            "utcDate": "2025-08-16T14:00:00Z",
            "status": "FINISHED",
            "matchday": 1,
            "homeTeam": {"id": 57, "name": "Arsenal FC", "tla": "ARS", "crest": "http://x/ars.png"},
            "awayTeam": {"id": 61, "name": "Chelsea FC", "tla": "CHE", "crest": "http://x/che.png"},
            "score": {"fullTime": {"home": 2, "away": 1}},
            "competition": {"code": "PL"},
        },
        {
            "id": 1002,
            "utcDate": "2025-08-17T16:00:00Z",
            "status": "IN_PLAY",
            "matchday": 1,
            "homeTeam": {"id": 61, "name": "Chelsea FC", "tla": "CHE", "crest": "http://x/che.png"},
            "awayTeam": {"id": 57, "name": "Arsenal FC", "tla": "ARS", "crest": "http://x/ars.png"},
            "score": {"fullTime": {"home": 0, "away": 0}},
            "competition": {"code": "PL"},
        },
    ]
}


class SyncStandingsTests(TestCase):
    def setUp(self):
        self.league = make_league(external_id="PL")

    @mock.patch("apps.sync.tasks.football_data.football_data_get")
    def test_creates_teams_and_standings(self, mocked_get):
        mocked_get.return_value = STANDINGS_RESPONSE
        fd.sync_standings(self.league.id)
        self.assertEqual(Team.objects.count(), 2)
        self.assertEqual(Standing.objects.count(), 2)
        top = Standing.objects.order_by("position").first()
        self.assertEqual(top.points, 25)
        self.assertEqual(top.team.name, "Arsenal FC")
        self.assertTrue(SyncLog.objects.filter(task="sync_standings", success=True).exists())

    @mock.patch("apps.sync.tasks.football_data.football_data_get")
    def test_idempotent(self, mocked_get):
        mocked_get.return_value = STANDINGS_RESPONSE
        fd.sync_standings(self.league.id)
        fd.sync_standings(self.league.id)
        self.assertEqual(Standing.objects.count(), 2)
        self.assertEqual(Team.objects.count(), 2)
        # second run should report updates, not creations
        last = SyncLog.objects.filter(task="sync_standings").order_by("-created_at").first()
        self.assertGreater(last.records_updated, 0)


class SyncFixturesTests(TestCase):
    def setUp(self):
        self.league = make_league(external_id="PL")

    @mock.patch("apps.sync.tasks.football_data.football_data_get")
    def test_maps_status_scores_and_raw_data(self, mocked_get):
        mocked_get.return_value = MATCHES_RESPONSE
        fd.sync_fixtures(self.league.id)
        self.assertEqual(Match.objects.count(), 2)
        finished = Match.objects.get(external_id="1001")
        self.assertEqual(finished.status, MatchStatus.FINISHED)
        self.assertEqual(finished.home_score, 2)
        self.assertEqual(finished.raw_data["id"], 1001)
        live = Match.objects.get(external_id="1002")
        self.assertEqual(live.status, MatchStatus.LIVE)

    @mock.patch("apps.sync.tasks.football_data.football_data_get")
    def test_results_idempotent(self, mocked_get):
        mocked_get.return_value = MATCHES_RESPONSE
        fd.sync_results(self.league.id)
        fd.sync_results(self.league.id)
        self.assertEqual(Match.objects.count(), 2)


class SyncLeaguesTests(TestCase):
    @mock.patch("apps.sync.tasks.football_data.football_data_get")
    def test_upserts_all_competitions(self, mocked_get):
        # Distinct name per competition path (real API returns unique names).
        def fake_get(path, params=None):
            code = path.split("/")[-1]
            return {
                "name": f"Competition {code}",
                "area": {"name": "Europe"},
                "currentSeason": {"startDate": "2025-08-01"},
            }

        mocked_get.side_effect = fake_get
        fd.sync_leagues()
        self.assertEqual(League.objects.count(), len(fd.FOOTBALL_DATA_COMPETITIONS))
