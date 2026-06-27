from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.common.test_factories import make_league, make_match, make_stats, make_team
from apps.matches.models import MatchStatus
from apps.predictions.models import MatchPrediction, Outcome
from apps.predictions.tasks import evaluate_predictions, run_daily_predictions
from ml import predict, train

from .test_ml import clean_models, seed_history


class RunDailyPredictionsTests(TestCase):
    def setUp(self):
        self.league = make_league()
        self.teams = [
            make_team(self.league, name=f"T{i}", external_id=str(i)) for i in range(5)
        ]
        seed_history(self.league, self.teams, n=45)
        self.today_match = make_match(
            self.league, self.teams[0], self.teams[1], external_id="today",
            status=MatchStatus.SCHEDULED, kickoff=timezone.now() + timedelta(hours=3),
        )

    def tearDown(self):
        clean_models()

    def test_returns_model_not_found_without_model(self):
        clean_models()
        result = run_daily_predictions()
        self.assertEqual(result, {"error": "model_not_found"})

    def test_creates_predictions_for_today(self):
        train.train("v1")
        result = run_daily_predictions()
        self.assertEqual(result["created"], 1)
        self.assertTrue(
            MatchPrediction.objects.filter(match=self.today_match).exists()
        )


class EvaluatePredictionsTaskTests(TestCase):
    def test_scores_finished_predictions(self):
        league = make_league()
        a = make_team(league, name="A", external_id="1")
        b = make_team(league, name="B", external_id="2")
        match = make_match(
            league, a, b, external_id="done",
            status=MatchStatus.FINISHED, home_score=0, away_score=2,
            kickoff=timezone.now() - timedelta(days=1),
        )
        MatchPrediction.objects.create(
            match=match, home_win_prob=0.2, draw_prob=0.2, away_win_prob=0.6,
            predicted_outcome=Outcome.AWAY, model_version="v1_logistic",
            confidence_score=0.6,
        )
        result = evaluate_predictions()
        self.assertEqual(result, {"scored": 1, "correct": 1})
        self.assertTrue(MatchPrediction.objects.get(match=match).was_correct)
