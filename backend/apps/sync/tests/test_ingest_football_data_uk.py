from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from apps.leagues.models import League, Source, Team
from apps.matches.models import Match, MatchStats, MatchStatus

CSV = (
    "Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,"
    "HS,AS,HST,AST,HC,AC,HF,AF,HY,AY,HR,AR\n"
    "E0,12/08/2023,15:00,Arsenal,Chelsea,2,1,H,"
    "14,7,6,3,8,4,11,13,1,2,0,1\n"
    "E0,13/08/2023,17:30,Liverpool,Man City,1,1,D,"
    "10,12,4,5,5,6,9,8,2,1,0,0\n"
)


def _fake_response(text, status=200):
    fake = mock.Mock()
    fake.status_code = status
    fake.content = text.encode("latin-1")
    return fake


class IngestFootballDataUkTests(TestCase):
    @mock.patch(
        "apps.sync.management.commands.ingest_football_data_uk.requests.get"
    )
    def test_creates_matches_and_stats(self, mocked_get):
        mocked_get.return_value = _fake_response(CSV)
        call_command("ingest_football_data_uk", "--division", "E0", "--season", "2324")

        league = League.objects.get(external_id="fduk-E0", source=Source.FOOTBALL_DATA)
        self.assertFalse(league.is_active)
        self.assertEqual(Match.objects.count(), 2)
        self.assertEqual(Team.objects.count(), 4)

        m = Match.objects.get(home_team__name="Arsenal")
        self.assertEqual(m.status, MatchStatus.FINISHED)
        self.assertEqual((m.home_score, m.away_score), (2, 1))
        stats = MatchStats.objects.get(match=m)
        self.assertEqual(stats.home_shots, 14)
        self.assertEqual(stats.away_shots_on_target, 3)
        self.assertEqual(stats.home_red_cards, 0)
        self.assertEqual(stats.away_red_cards, 1)

    @mock.patch(
        "apps.sync.management.commands.ingest_football_data_uk.requests.get"
    )
    def test_idempotent(self, mocked_get):
        mocked_get.return_value = _fake_response(CSV)
        call_command("ingest_football_data_uk", "--division", "E0", "--season", "2324")
        mocked_get.return_value = _fake_response(CSV)
        call_command("ingest_football_data_uk", "--division", "E0", "--season", "2324")
        self.assertEqual(Match.objects.count(), 2)
        self.assertEqual(MatchStats.objects.count(), 2)

    @mock.patch(
        "apps.sync.management.commands.ingest_football_data_uk.requests.get"
    )
    def test_missing_season_skipped(self, mocked_get):
        mocked_get.return_value = _fake_response("", status=404)
        call_command("ingest_football_data_uk", "--division", "E0", "--season", "9999")
        self.assertEqual(Match.objects.count(), 0)
