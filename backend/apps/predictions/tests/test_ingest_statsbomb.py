from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.leagues.models import League
from apps.matches.models import Match, MatchStats

COMPETITIONS = [
    {"competition_id": 11, "season_id": 90, "competition_name": "La Liga", "season_name": "2019/2020"},
    {"competition_id": 11, "season_id": 90, "competition_name": "La Liga", "season_name": "2019/2020"},  # dup
]

MATCHES = [
    {
        "match_id": 3773386,
        "match_date": "2020-06-16",
        "kick_off": "22:00:00.000",
        "home_team": {"home_team_id": 217, "home_team_name": "Barcelona"},
        "away_team": {"away_team_id": 206, "away_team_name": "Leganes"},
        "home_score": 2,
        "away_score": 0,
        "competition": {"competition_name": "La Liga", "country_name": "Spain"},
        "season": {"season_name": "2019/2020"},
    }
]

EVENTS = [
    {"type": {"name": "Shot"}, "team": {"name": "Barcelona"}, "shot": {"statsbomb_xg": 0.4}},
    {"type": {"name": "Shot"}, "team": {"name": "Barcelona"}, "shot": {"statsbomb_xg": 0.2}},
    {"type": {"name": "Shot"}, "team": {"name": "Leganes"}, "shot": {"statsbomb_xg": 0.1}},
    {"type": {"name": "Pass"}, "team": {"name": "Barcelona"}},
]


def fake_get(url):
    if url.endswith("competitions.json"):
        return COMPETITIONS
    if "/matches/" in url:
        return MATCHES
    if "/events/" in url:
        return EVENTS
    raise AssertionError(f"unexpected url {url}")


class IngestStatsbombTests(TestCase):
    @mock.patch("apps.predictions.management.commands.ingest_statsbomb._get", side_effect=fake_get)
    def test_single_competition_season(self, _mock):
        call_command("ingest_statsbomb", "--competition", "11", "--season", "90")
        self.assertEqual(Match.objects.count(), 1)
        stats = MatchStats.objects.get()
        self.assertAlmostEqual(stats.home_xg, 0.6, places=3)
        self.assertAlmostEqual(stats.away_xg, 0.1, places=3)

    @mock.patch("apps.predictions.management.commands.ingest_statsbomb._get", side_effect=fake_get)
    def test_all_dedupes_pairs(self, _mock):
        call_command("ingest_statsbomb", "--all")
        # COMPETITIONS has a duplicate pair -> only one league/match ingested.
        self.assertEqual(League.objects.count(), 1)
        self.assertEqual(Match.objects.count(), 1)

    def test_requires_competition_or_all(self):
        with self.assertRaises(CommandError):
            call_command("ingest_statsbomb")
