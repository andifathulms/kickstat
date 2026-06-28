from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.leagues.models import League
from apps.matches.models import Match, MatchStats
from apps.predictions.management.commands.ingest_statsbomb import compute_match_stats

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
        # full stat line is now populated (possession marks completeness)
        self.assertIsNotNone(stats.home_possession)
        self.assertEqual(stats.home_shots, 2)

    @mock.patch("apps.predictions.management.commands.ingest_statsbomb._get", side_effect=fake_get)
    def test_all_dedupes_pairs(self, _mock):
        call_command("ingest_statsbomb", "--all")
        # COMPETITIONS has a duplicate pair -> only one league/match ingested.
        self.assertEqual(League.objects.count(), 1)
        self.assertEqual(Match.objects.count(), 1)

    def test_requires_competition_or_all(self):
        with self.assertRaises(CommandError):
            call_command("ingest_statsbomb")


class ComputeMatchStatsTests(TestCase):
    EVENTS = [
        {"type": {"name": "Shot"}, "team": {"name": "H"},
         "shot": {"statsbomb_xg": 0.5, "outcome": {"name": "Goal"}}},
        {"type": {"name": "Shot"}, "team": {"name": "H"},
         "shot": {"statsbomb_xg": 0.1, "outcome": {"name": "Off T"}}},
        {"type": {"name": "Shot"}, "team": {"name": "A"},
         "shot": {"statsbomb_xg": 0.3, "outcome": {"name": "Saved"}}},
        {"type": {"name": "Pass"}, "team": {"name": "H"}},
        {"type": {"name": "Pass"}, "team": {"name": "H"},
         "pass": {"type": {"name": "Corner"}}},
        {"type": {"name": "Pass"}, "team": {"name": "A"}},
        {"type": {"name": "Foul Committed"}, "team": {"name": "A"},
         "foul_committed": {"card": {"name": "Yellow Card"}}},
        {"type": {"name": "Bad Behaviour"}, "team": {"name": "A"},
         "bad_behaviour": {"card": {"name": "Red Card"}}},
        {"type": {"name": "Foul Committed"}, "team": {"name": "H"}},
    ]

    def test_full_stat_line(self):
        s = compute_match_stats(self.EVENTS, "H", "A")
        self.assertEqual((s["home_shots"], s["away_shots"]), (2, 1))
        self.assertEqual((s["home_shots_on_target"], s["away_shots_on_target"]), (1, 1))
        self.assertAlmostEqual(s["home_xg"], 0.6, places=3)
        self.assertAlmostEqual(s["away_xg"], 0.3, places=3)
        self.assertEqual((s["home_corners"], s["away_corners"]), (1, 0))
        self.assertEqual((s["home_fouls"], s["away_fouls"]), (1, 1))
        self.assertEqual((s["away_yellow_cards"], s["away_red_cards"]), (1, 1))
        # possession by passes-share: H=2, A=1 -> ~66.7 / 33.3
        self.assertAlmostEqual(s["home_possession"], 66.7, places=1)
        self.assertAlmostEqual(s["away_possession"], 33.3, places=1)

    def test_second_yellow_counts_as_yellow_and_red(self):
        events = [
            {"type": {"name": "Foul Committed"}, "team": {"name": "A"},
             "foul_committed": {"card": {"name": "Second Yellow"}}},
        ]
        s = compute_match_stats(events, "H", "A")
        self.assertEqual((s["away_yellow_cards"], s["away_red_cards"]), (1, 1))

    def test_no_events_possession_none(self):
        s = compute_match_stats([], "H", "A")
        self.assertIsNone(s["home_possession"])
        self.assertEqual(s["home_shots"], 0)
