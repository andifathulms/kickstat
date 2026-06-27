from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.common.test_factories import make_league, make_match, make_stats, make_team
from apps.matches.models import MatchStatus
from ml import evaluate, features, predict, train


def seed_history(league, teams, n=40, base_days=120):
    """Create n finished matches cycling through teams, with deterministic scores."""
    start = timezone.now() - timedelta(days=base_days)
    for i in range(n):
        home = teams[i % len(teams)]
        away = teams[(i + 1) % len(teams)]
        hs, as_ = (i % 3), ((i + 1) % 2)
        m = make_match(
            league, home, away, external_id=f"hist-{i}",
            status=MatchStatus.FINISHED, home_score=hs, away_score=as_,
            kickoff=start + timedelta(days=i),
        )
        make_stats(m, home_xg=hs + 0.3, away_xg=as_ + 0.2)


class FeatureTests(TestCase):
    def setUp(self):
        self.league = make_league()
        self.teams = [
            make_team(self.league, name=f"T{i}", external_id=str(i)) for i in range(4)
        ]
        seed_history(self.league, self.teams, n=20)
        self.upcoming = make_match(
            self.league, self.teams[0], self.teams[1], external_id="up",
            status=MatchStatus.SCHEDULED, kickoff=timezone.now() + timedelta(days=1),
        )

    def test_returns_full_feature_schema(self):
        feats = features.get_features(self.upcoming.id)
        self.assertEqual(set(feats.keys()), set(features.FEATURE_ORDER))

    def test_home_advantage_constant(self):
        feats = features.get_features(self.upcoming.id)
        self.assertEqual(feats["home_advantage"], 1)

    def test_vector_matches_order(self):
        feats = features.get_features(self.upcoming.id)
        vector = features.features_to_vector(feats)
        self.assertEqual(len(vector), len(features.FEATURE_ORDER))
        self.assertEqual(vector[0], feats[features.FEATURE_ORDER[0]])


class TrainPredictEvaluateTests(TestCase):
    def setUp(self):
        self.league = make_league()
        self.teams = [
            make_team(self.league, name=f"T{i}", external_id=str(i)) for i in range(5)
        ]
        seed_history(self.league, self.teams, n=45)

    def tearDown(self):
        # Remove the serialized model written to ml/models and reset the cache.
        if train.MODEL_PATH.exists():
            train.MODEL_PATH.unlink()
        predict._cache.clear()

    def test_train_writes_model(self):
        path = train.train()
        self.assertTrue(path.exists())

    def test_predict_returns_normalised_probabilities(self):
        train.train()
        upcoming = make_match(
            self.league, self.teams[0], self.teams[1], external_id="up",
            status=MatchStatus.SCHEDULED, kickoff=timezone.now() + timedelta(days=1),
        )
        result = predict.predict_match(upcoming.id)
        total = result["home_win_prob"] + result["draw_prob"] + result["away_win_prob"]
        self.assertAlmostEqual(total, 1.0, places=2)
        self.assertIn(result["predicted_outcome"], {"HOME", "DRAW", "AWAY"})
        self.assertEqual(result["model_version"], "v1_logistic")

    def test_evaluate_fills_was_correct(self):
        from apps.predictions.models import MatchPrediction, Outcome

        match = make_match(
            self.league, self.teams[0], self.teams[1], external_id="ev",
            status=MatchStatus.FINISHED, home_score=2, away_score=0,
            kickoff=timezone.now() - timedelta(days=1),
        )
        MatchPrediction.objects.create(
            match=match, home_win_prob=0.6, draw_prob=0.25, away_win_prob=0.15,
            predicted_outcome=Outcome.HOME, model_version="v1_logistic",
            confidence_score=0.6,
        )
        scored, correct = evaluate.evaluate_unscored()
        self.assertEqual((scored, correct), (1, 1))
        self.assertEqual(evaluate.accuracy_by_version()["v1_logistic"], 1.0)
