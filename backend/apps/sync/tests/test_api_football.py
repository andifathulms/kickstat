from unittest import mock

from django.core.cache import cache
from django.test import TestCase

from apps.leagues.models import League, Source, Team
from apps.matches.models import Match, MatchStatus
from apps.sync.tasks import api_football as af

FIXTURES_RESPONSE = {
    "response": [
        {
            "fixture": {
                "id": 880001,
                "date": "2025-09-01T12:00:00+00:00",
                "status": {"short": "NS"},
            },
            "league": {"round": "Regular Season - 1"},
            "teams": {
                "home": {"id": 1, "name": "Persija Jakarta", "logo": "http://x/persija.png"},
                "away": {"id": 2, "name": "Persib Bandung", "logo": "http://x/persib.png"},
            },
            "goals": {"home": None, "away": None},
        },
        {
            "fixture": {
                "id": 880002,
                "date": "2025-09-02T12:00:00+00:00",
                "status": {"short": "FT"},
            },
            "league": {"round": "Regular Season - 1"},
            "teams": {
                "home": {"id": 2, "name": "Persib Bandung", "logo": "http://x/persib.png"},
                "away": {"id": 1, "name": "Persija Jakarta", "logo": "http://x/persija.png"},
            },
            "goals": {"home": 2, "away": 1},
        },
    ]
}


class Liga1SyncTests(TestCase):
    def setUp(self):
        cache.clear()

    @mock.patch("apps.sync.tasks.api_football.api_football_get")
    def test_fixtures_create_league_teams_matches(self, mocked_get):
        mocked_get.return_value = FIXTURES_RESPONSE
        af.sync_liga1_fixtures()
        league = League.objects.get(source=Source.API_FOOTBALL)
        self.assertEqual(league.name, "Liga 1")
        self.assertEqual(league.country, "Indonesia")
        self.assertEqual(Team.objects.count(), 2)
        self.assertEqual(Match.objects.count(), 2)

    @mock.patch("apps.sync.tasks.api_football.api_football_get")
    def test_status_and_scores_mapped(self, mocked_get):
        mocked_get.return_value = FIXTURES_RESPONSE
        af.sync_liga1_results()
        scheduled = Match.objects.get(external_id="880001")
        self.assertEqual(scheduled.status, MatchStatus.SCHEDULED)
        finished = Match.objects.get(external_id="880002")
        self.assertEqual(finished.status, MatchStatus.FINISHED)
        self.assertEqual(finished.home_score, 2)

    @mock.patch("apps.sync.tasks.api_football.api_football_get")
    def test_idempotent(self, mocked_get):
        mocked_get.return_value = FIXTURES_RESPONSE
        af.sync_liga1_fixtures()
        af.sync_liga1_fixtures()
        self.assertEqual(Match.objects.count(), 2)
        self.assertEqual(League.objects.filter(source=Source.API_FOOTBALL).count(), 1)
