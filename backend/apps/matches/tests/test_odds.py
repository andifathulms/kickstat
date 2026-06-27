from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APITestCase

from apps.common.test_factories import make_league, make_match, make_team
from apps.matches.management.commands.backfill_odds import extract_odds
from apps.matches.models import MatchOdds, MatchStatus


class ExtractOddsTests(TestCase):
    def test_prefers_market_average(self):
        row = {"AvgH": "2.1", "AvgD": "3.4", "AvgA": "3.6", "B365H": "2.0"}
        h, d, a, o, u = extract_odds(row)
        self.assertEqual((h, d, a), (2.1, 3.4, 3.6))

    def test_falls_back_to_bet365(self):
        row = {"B365H": "1.8", "B365D": "3.5", "B365A": "4.5",
               "B365>2.5": "1.9", "B365<2.5": "1.9"}
        h, d, a, o, u = extract_odds(row)
        self.assertEqual((h, d, a, o, u), (1.8, 3.5, 4.5, 1.9, 1.9))

    def test_empty_row(self):
        self.assertEqual(extract_odds({}), (None, None, None, None, None))

    def test_ignores_NA(self):
        row = {"AvgH": "NA", "B365H": "2.0", "AvgD": "3.0", "AvgA": "4.0"}
        h, d, a, _, _ = extract_odds(row)
        self.assertEqual((h, d, a), (2.0, 3.0, 4.0))


class ImpliedProbabilityTests(TestCase):
    def test_devigged_probs_sum_to_one(self):
        league = make_league()
        a = make_team(league, name="A", external_id="1")
        b = make_team(league, name="B", external_id="2")
        m = make_match(league, a, b, external_id="m1")
        odds = MatchOdds.objects.create(match=m, home_odds=2.0, draw_odds=3.0, away_odds=4.0)
        p = odds.implied_probabilities
        self.assertAlmostEqual(p["home"] + p["draw"] + p["away"], 1.0, places=3)
        self.assertGreater(p["home"], p["away"])

    def test_none_when_incomplete(self):
        league = make_league()
        a = make_team(league, name="A", external_id="1")
        b = make_team(league, name="B", external_id="2")
        m = make_match(league, a, b, external_id="m1")
        odds = MatchOdds.objects.create(match=m, home_odds=2.0)  # no draw/away
        self.assertIsNone(odds.implied_probabilities)


class BackfillOddsCommandTests(TestCase):
    def test_backfills_from_raw_data(self):
        league = make_league(name="PL (history)", external_id="fduk-E0", is_active=False)
        a = make_team(league, name="A", external_id="ha")
        b = make_team(league, name="B", external_id="hb")
        make_match(
            league, a, b, external_id="fduk-E0-2425-a-b", status=MatchStatus.FINISHED,
            home_score=1, away_score=0,
            raw_data={"AvgH": "1.9", "AvgD": "3.5", "AvgA": "4.2", "Avg>2.5": "2.0"},
        )
        make_match(  # no odds in raw_data -> skipped
            league, a, b, external_id="fduk-E0-2425-c-d", status=MatchStatus.FINISHED,
            home_score=2, away_score=2, raw_data={"FTHG": "2"},
        )
        call_command("backfill_odds")
        self.assertEqual(MatchOdds.objects.count(), 1)
        o = MatchOdds.objects.get()
        self.assertEqual(o.home_odds, 1.9)
        self.assertEqual(o.over25_odds, 2.0)


class OddsAPITests(APITestCase):
    def test_detail_includes_odds_with_implied_probs(self):
        league = make_league()
        a = make_team(league, name="A", external_id="1")
        b = make_team(league, name="B", external_id="2")
        m = make_match(league, a, b, external_id="m1", status=MatchStatus.FINISHED,
                       home_score=1, away_score=0)
        MatchOdds.objects.create(match=m, home_odds=2.0, draw_odds=3.0, away_odds=4.0)
        resp = self.client.get(f"/api/matches/{m.id}/")
        self.assertEqual(resp.status_code, 200)
        odds = resp.json()["odds"]
        self.assertEqual(odds["home_odds"], 2.0)
        self.assertIn("implied_probabilities", odds)
        self.assertAlmostEqual(sum(odds["implied_probabilities"].values()), 1.0, places=3)
