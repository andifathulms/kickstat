from datetime import timedelta
from unittest import skipUnless

from django.test import TestCase
from django.utils import timezone

from apps.common.test_factories import make_league, make_match, make_stats, make_team
from apps.matches.models import MatchStatus
from ml import evaluate, features, predict, train


def clean_models():
    """Remove any serialized models written during a test and reset the cache."""
    for stem in ("v1_logistic", "v2_xgboost", "v3_xgboost"):
        path = predict._model_path(stem)
        if path.exists():
            path.unlink()
    predict._cache.clear()


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
        make_stats(
            m,
            home_xg=hs + 0.3, away_xg=as_ + 0.2,
            home_shots=hs + 8, away_shots=as_ + 6,
            home_shots_on_target=hs + 2, away_shots_on_target=as_ + 1,
        )


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

    def test_v2_feature_schema_extends_v1(self):
        feats = features.get_features_v2(self.upcoming.id)
        self.assertEqual(set(feats.keys()), set(features.FEATURE_ORDER_V2))
        # v2 is a superset of v1
        self.assertTrue(set(features.FEATURE_ORDER).issubset(feats.keys()))
        for key in (
            "home_sot_ratio",
            "away_sot_ratio",
            "home_days_rest",
            "away_days_rest",
            "home_venue_form_pts",
            "away_venue_form_pts",
        ):
            self.assertIn(key, feats)

    def test_v2_vector_length(self):
        feats = features.get_features_v2(self.upcoming.id)
        vector = features.features_to_vector(feats, features.FEATURE_ORDER_V2)
        self.assertEqual(len(vector), len(features.FEATURE_ORDER_V2))

    def test_v3_feature_schema_extends_v2(self):
        feats = features.get_features_v3(self.upcoming.id)
        self.assertEqual(set(feats.keys()), set(features.FEATURE_ORDER_V3))
        self.assertTrue(set(features.FEATURE_ORDER_V2).issubset(feats.keys()))
        for key in (
            "home_market_strength",
            "away_market_strength",
            "home_shots_avg",
            "home_possession_avg",
            "home_corners_avg",
        ):
            self.assertIn(key, feats)


class MarketStrengthFeatureTests(TestCase):
    def setUp(self):
        from apps.matches.models import MatchOdds

        self.league = make_league()
        self.home = make_team(self.league, name="Strong", external_id="h")
        self.away = make_team(self.league, name="Weak", external_id="a")
        # Two past matches where the market rated Strong as a heavy home favourite.
        for i in range(2):
            m = make_match(
                self.league, self.home, self.away, external_id=f"p{i}",
                status=MatchStatus.FINISHED, home_score=2, away_score=0,
                kickoff=timezone.now() - timedelta(days=10 + i),
            )
            MatchOdds.objects.create(
                match=m, home_odds=1.25, draw_odds=6.0, away_odds=12.0
            )
        self.upcoming = make_match(
            self.league, self.home, self.away, external_id="up",
            status=MatchStatus.SCHEDULED, kickoff=timezone.now() + timedelta(days=1),
        )

    def test_market_strength_reflects_recent_odds(self):
        feats = features.get_features_v3(self.upcoming.id)
        # Strong team's implied win prob from 1.25 odds (de-vigged) is high.
        self.assertGreater(feats["home_market_strength"], 0.7)
        self.assertLess(feats["away_market_strength"], 0.15)


class TrainPredictEvaluateTests(TestCase):
    def setUp(self):
        self.league = make_league()
        self.teams = [
            make_team(self.league, name=f"T{i}", external_id=str(i)) for i in range(5)
        ]
        seed_history(self.league, self.teams, n=45)

    def tearDown(self):
        clean_models()

    def test_train_writes_model(self):
        path = train.train("v1")
        self.assertTrue(path.exists())

    def test_predict_returns_normalised_probabilities(self):
        train.train("v1")
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


try:
    import xgboost  # noqa: F401

    HAS_XGBOOST = True
except Exception:  # noqa: BLE001 — XGBoostError (missing libomp) is not ImportError
    HAS_XGBOOST = False


@skipUnless(HAS_XGBOOST, "xgboost not installed in this environment")
class XGBoostModelTests(TestCase):
    def setUp(self):
        self.league = make_league()
        self.teams = [
            make_team(self.league, name=f"T{i}", external_id=str(i)) for i in range(5)
        ]
        seed_history(self.league, self.teams, n=60)

    def tearDown(self):
        clean_models()

    def test_train_v2_writes_xgboost_model(self):
        path = train.train("v2")
        self.assertTrue(str(path).endswith("v2_xgboost.pkl"))
        self.assertTrue(path.exists())

    def test_predict_uses_active_v2_model(self):
        train.train("v2")
        upcoming = make_match(
            self.league, self.teams[0], self.teams[1], external_id="up2",
            status=MatchStatus.SCHEDULED, kickoff=timezone.now() + timedelta(days=1),
        )
        result = predict.predict_match(upcoming.id)
        self.assertEqual(result["model_version"], "v2_xgboost")
        total = result["home_win_prob"] + result["draw_prob"] + result["away_win_prob"]
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_v2_preferred_over_v1_when_both_present(self):
        train.train("v1")
        train.train("v2")
        self.assertTrue(str(predict.resolve_model_path()).endswith("v2_xgboost.pkl"))

    def test_train_and_predict_v3(self):
        train.train("v3")
        upcoming = make_match(
            self.league, self.teams[0], self.teams[1], external_id="up3",
            status=MatchStatus.SCHEDULED, kickoff=timezone.now() + timedelta(days=1),
        )
        result = predict.predict_match(upcoming.id)
        self.assertEqual(result["model_version"], "v3_xgboost")
        total = result["home_win_prob"] + result["draw_prob"] + result["away_win_prob"]
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_v3_preferred_when_present(self):
        train.train("v2")
        train.train("v3")
        self.assertTrue(str(predict.resolve_model_path()).endswith("v3_xgboost.pkl"))
