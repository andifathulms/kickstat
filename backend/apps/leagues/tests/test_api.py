from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.common.test_factories import (
    make_league,
    make_match,
    make_standing,
    make_team,
)
from apps.matches.models import MatchStatus


class LeagueAPITests(APITestCase):
    def setUp(self):
        self.league = make_league()
        self.home = make_team(self.league, name="Arsenal", external_id="57")
        self.away = make_team(self.league, name="Chelsea", external_id="61")
        make_standing(self.league, self.home, position=1)
        make_standing(self.league, self.away, position=2, points=20)

    def test_league_list_paginated(self):
        resp = self.client.get("/api/leagues/")
        self.assertEqual(resp.status_code, 200)
        for key in ("count", "next", "previous", "results"):
            self.assertIn(key, resp.json())

    def test_standings_ordered_by_position(self):
        resp = self.client.get(f"/api/leagues/{self.league.id}/standings/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual([s["position"] for s in data], [1, 2])
        self.assertEqual(data[0]["team"]["name"], "Arsenal")

    def test_league_lookup_by_slug(self):
        resp = self.client.get(f"/api/leagues/{self.league.slug}/standings/")
        self.assertEqual(resp.status_code, 200)

    def test_archive_lists_historical_leagues_with_counts(self):
        hist = make_league(
            name="Premier League (history)", external_id="fduk-E0", is_active=False
        )
        a = make_team(hist, name="A", external_id="ha")
        b = make_team(hist, name="B", external_id="hb")
        make_match(
            hist, a, b, external_id="h1", status=MatchStatus.FINISHED,
            home_score=1, away_score=0, kickoff=timezone.now() - timedelta(days=400),
        )
        resp = self.client.get("/api/leagues/archive/")
        self.assertEqual(resp.status_code, 200)
        entries = resp.json()
        slugs = [e["slug"] for e in entries]
        self.assertIn(hist.slug, slugs)
        self.assertNotIn(self.league.slug, slugs)  # active league excluded
        entry = next(e for e in entries if e["slug"] == hist.slug)
        self.assertEqual(entry["match_count"], 1)
        self.assertEqual(entry["first_year"], entry["last_year"])

    def test_fixtures_excludes_finished(self):
        make_match(self.league, self.home, self.away, external_id="up", status=MatchStatus.SCHEDULED)
        make_match(
            self.league, self.home, self.away, external_id="done",
            status=MatchStatus.FINISHED, kickoff=timezone.now() - timedelta(days=1),
            home_score=2, away_score=1,
        )
        resp = self.client.get(f"/api/leagues/{self.league.id}/fixtures/")
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "SCHEDULED")


class TeamAPITests(APITestCase):
    def setUp(self):
        self.league = make_league()
        self.home = make_team(self.league, name="Arsenal", external_id="57")
        self.away = make_team(self.league, name="Chelsea", external_id="61")

    def test_team_form_returns_last_finished(self):
        make_match(
            self.league, self.home, self.away, external_id="f1",
            status=MatchStatus.FINISHED, kickoff=timezone.now() - timedelta(days=3),
            home_score=2, away_score=0,
        )
        resp = self.client.get(f"/api/teams/{self.home.id}/form/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_team_stats_aggregates_goals(self):
        make_match(
            self.league, self.home, self.away, external_id="f1",
            status=MatchStatus.FINISHED, kickoff=timezone.now() - timedelta(days=3),
            home_score=3, away_score=1,
        )
        resp = self.client.get(f"/api/teams/{self.home.id}/stats/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["goals_scored"], 3)
        self.assertEqual(body["goals_conceded"], 1)
        self.assertEqual(body["goals_scored_avg"], 3.0)
