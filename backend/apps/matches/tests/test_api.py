from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.common.test_factories import (
    make_league,
    make_match,
    make_stats,
    make_team,
)
from apps.matches.models import EventType, MatchEvent, MatchStatus
from apps.predictions.models import MatchPrediction, Outcome


class MatchAPITests(APITestCase):
    def setUp(self):
        self.league = make_league()
        self.home = make_team(self.league, name="Arsenal", external_id="57")
        self.away = make_team(self.league, name="Chelsea", external_id="61")
        self.live = make_match(
            self.league, self.home, self.away, external_id="live1",
            status=MatchStatus.LIVE, home_score=1, away_score=0,
        )
        make_stats(self.live, home_possession=58, away_possession=42, home_xg=1.8, away_xg=0.9)
        MatchEvent.objects.create(match=self.live, minute=23, type=EventType.GOAL, team=self.home)
        MatchPrediction.objects.create(
            match=self.live, home_win_prob=0.55, draw_prob=0.25, away_win_prob=0.20,
            predicted_outcome=Outcome.HOME, model_version="v1_logistic", confidence_score=0.55,
        )

    def test_list_paginated(self):
        resp = self.client.get("/api/matches/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("results", resp.json())

    def test_detail_nests_stats_events_prediction(self):
        resp = self.client.get(f"/api/matches/{self.live.id}/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["home_team"]["name"], "Arsenal")
        self.assertEqual(body["stats"]["home_possession"], 58)
        self.assertEqual(len(body["events"]), 1)
        self.assertEqual(body["prediction"]["predicted_outcome"], "HOME")
        self.assertIsInstance(body["league"], dict)

    def test_live_endpoint_only_live(self):
        make_match(
            self.league, self.home, self.away, external_id="sched",
            status=MatchStatus.SCHEDULED,
        )
        resp = self.client.get("/api/matches/live/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["status"], "LIVE")

    def test_filter_by_status(self):
        make_match(
            self.league, self.home, self.away, external_id="sched",
            status=MatchStatus.SCHEDULED,
        )
        resp = self.client.get("/api/matches/?status=SCHEDULED")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 1)

    def test_filter_by_date(self):
        day = (timezone.now() + timedelta(days=5)).date()
        make_match(
            self.league, self.home, self.away, external_id="future",
            status=MatchStatus.SCHEDULED,
            kickoff=timezone.now() + timedelta(days=5),
        )
        resp = self.client.get(f"/api/matches/?date={day.isoformat()}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 1)

    def test_prediction_endpoint_404_when_missing(self):
        bare = make_match(
            self.league, self.home, self.away, external_id="nopred",
            status=MatchStatus.SCHEDULED,
        )
        resp = self.client.get(f"/api/matches/{bare.id}/prediction/")
        self.assertEqual(resp.status_code, 404)
