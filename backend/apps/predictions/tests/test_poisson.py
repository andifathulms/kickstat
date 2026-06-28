from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.common.test_factories import make_league, make_match, make_team
from apps.matches.models import MatchStatus
from apps.predictions.models import MatchScorePrediction
from apps.predictions.tasks import run_score_predictions
from ml import poisson


def _seed(league, scorer, weak, n=8):
    """Finished history: `scorer` wins big at home, `weak` loses."""
    base = timezone.now() - timedelta(days=60)
    for i in range(n):
        make_match(
            league, scorer, weak, external_id=f"s{i}",
            status=MatchStatus.FINISHED, home_score=3, away_score=0,
            kickoff=base + timedelta(days=i),
        )


class PoissonComputeTests(TestCase):
    def setUp(self):
        poisson._baseline_cache.clear()
        self.league = make_league()
        self.strong = make_team(self.league, name="Strong", external_id="s")
        self.weak = make_team(self.league, name="Weak", external_id="w")
        _seed(self.league, self.strong, self.weak)
        self.upcoming = make_match(
            self.league, self.strong, self.weak, external_id="up",
            status=MatchStatus.SCHEDULED, kickoff=timezone.now() + timedelta(days=1),
        )

    def test_probabilities_sum_to_one(self):
        r = poisson.predict_scoreline(self.upcoming.id)
        total = r["home_win_prob"] + r["draw_prob"] + r["away_win_prob"]
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_strong_home_team_favoured(self):
        r = poisson.predict_scoreline(self.upcoming.id)
        self.assertGreater(r["lambda_home"], r["lambda_away"])
        self.assertGreater(r["home_win_prob"], r["away_win_prob"])
        # most likely score has home >= away for a dominant home side
        self.assertGreaterEqual(r["most_likely_home"], r["most_likely_away"])

    def test_top_scores_structure(self):
        r = poisson.predict_scoreline(self.upcoming.id)
        self.assertEqual(len(r["top_scores"]), 5)
        self.assertIn("home", r["top_scores"][0])
        self.assertIn("prob", r["top_scores"][0])
        # top scores are sorted by probability descending
        probs = [s["prob"] for s in r["top_scores"]]
        self.assertEqual(probs, sorted(probs, reverse=True))


class RunScorePredictionsTaskTests(TestCase):
    def setUp(self):
        poisson._baseline_cache.clear()
        self.league = make_league()
        self.strong = make_team(self.league, name="Strong", external_id="s")
        self.weak = make_team(self.league, name="Weak", external_id="w")
        _seed(self.league, self.strong, self.weak)
        self.today = make_match(
            self.league, self.strong, self.weak, external_id="today",
            status=MatchStatus.SCHEDULED, kickoff=timezone.now() + timedelta(hours=2),
        )

    def test_creates_score_prediction(self):
        result = run_score_predictions()
        self.assertEqual(result["created"], 1)
        sp = MatchScorePrediction.objects.get(match=self.today)
        self.assertEqual(sp.model_version, "poisson_v1")
        self.assertGreaterEqual(sp.most_likely_home, 0)


class ScorePredictionAPITests(APITestCase):
    def test_detail_includes_score_prediction(self):
        poisson._baseline_cache.clear()
        league = make_league()
        a = make_team(league, name="A", external_id="a")
        b = make_team(league, name="B", external_id="b")
        m = make_match(league, a, b, external_id="m1", status=MatchStatus.SCHEDULED,
                       kickoff=timezone.now() + timedelta(days=1))
        MatchScorePrediction.objects.create(
            match=m, lambda_home=1.8, lambda_away=1.0,
            most_likely_home=1, most_likely_away=0, most_likely_prob=0.12,
            home_win_prob=0.55, draw_prob=0.25, away_win_prob=0.20,
            over25_prob=0.45, btts_prob=0.4,
            top_scores=[{"home": 1, "away": 0, "prob": 0.12}],
        )
        resp = self.client.get(f"/api/matches/{m.id}/")
        self.assertEqual(resp.status_code, 200)
        sp = resp.json()["score_prediction"]
        self.assertEqual(sp["most_likely_home"], 1)
        self.assertEqual(len(sp["top_scores"]), 1)
