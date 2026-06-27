from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.common.test_factories import make_league, make_match, make_team
from apps.matches.models import MatchStatus
from apps.predictions.models import MatchPrediction, Outcome
from ml.evaluate import accuracy_report


def _prediction(match, outcome=Outcome.HOME, version="v2_xgboost", correct=None):
    return MatchPrediction.objects.create(
        match=match,
        home_win_prob=0.6,
        draw_prob=0.25,
        away_win_prob=0.15,
        predicted_outcome=outcome,
        model_version=version,
        confidence_score=0.6,
        was_correct=correct,
    )


class AccuracyReportTests(TestCase):
    def setUp(self):
        self.league = make_league()
        self.a = make_team(self.league, name="A", external_id="1")
        self.b = make_team(self.league, name="B", external_id="2")

    def _match(self, ext, **kw):
        return make_match(self.league, self.a, self.b, external_id=ext, **kw)

    def test_report_counts_and_accuracy(self):
        m1 = self._match("m1", status=MatchStatus.FINISHED, home_score=2, away_score=0)
        m2 = self._match("m2", status=MatchStatus.FINISHED, home_score=0, away_score=1)
        m3 = self._match("m3", status=MatchStatus.SCHEDULED,
                         kickoff=timezone.now() + timedelta(days=1))
        _prediction(m1, correct=True)
        _prediction(m2, correct=False)
        _prediction(m3, correct=None)  # pending

        report = accuracy_report()
        self.assertEqual(len(report), 1)
        row = report[0]
        self.assertEqual(row["version"], "v2_xgboost")
        self.assertEqual(row["total"], 3)
        self.assertEqual(row["scored"], 2)
        self.assertEqual(row["correct"], 1)
        self.assertEqual(row["pending"], 1)
        self.assertEqual(row["accuracy_pct"], 50.0)

    def test_versions_sorted_by_accuracy(self):
        m1 = self._match("m1", status=MatchStatus.FINISHED, home_score=2, away_score=0)
        m2 = self._match("m2", status=MatchStatus.FINISHED, home_score=2, away_score=0)
        _prediction(m1, version="v1_logistic", correct=False)
        _prediction(m2, version="v2_xgboost", correct=True)
        report = accuracy_report()
        self.assertEqual(report[0]["version"], "v2_xgboost")  # higher accuracy first


class AdminDashboardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser("admin", "a@b.c", "pw")
        self.client.force_login(self.admin)
        league = make_league()
        a = make_team(league, name="A", external_id="1")
        b = make_team(league, name="B", external_id="2")
        m = make_match(league, a, b, external_id="m1",
                       status=MatchStatus.FINISHED, home_score=2, away_score=0)
        _prediction(m, correct=True)

    def test_changelist_renders_accuracy_panel(self):
        url = reverse("admin:predictions_matchprediction_changelist")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Prediction accuracy by model version")
        self.assertContains(resp, "v2_xgboost")
