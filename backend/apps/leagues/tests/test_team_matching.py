from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.common.test_factories import make_league, make_match, make_team
from apps.leagues.models import Source, Team
from apps.leagues.team_matching import match_name, normalize
from apps.matches.models import MatchStatus
from ml.features import get_features


class NormalizeTests(TestCase):
    def test_strips_accents_suffixes_punctuation(self):
        self.assertEqual(normalize("Atlético Madrid"), "atletico madrid")
        self.assertEqual(normalize("Brighton & Hove Albion FC"), "brighton and hove albion")
        self.assertEqual(normalize("Nott'm Forest"), "nottm forest")


class MatchNameTests(TestCase):
    def test_exact_normalized(self):
        self.assertEqual(match_name("Arsenal FC", ["Arsenal", "Chelsea"]), "Arsenal")

    def test_token_subset(self):
        self.assertEqual(
            match_name("Newcastle United FC", ["Newcastle", "Norwich"]), "Newcastle"
        )

    def test_alias(self):
        self.assertEqual(match_name("Manchester City FC", ["Man City", "Leeds"]), "Man City")

    def test_fuzzy(self):
        # Single-token spelling variation within the fuzzy cutoff.
        self.assertEqual(match_name("Sevilla", ["Sevila", "Valencia"]), "Sevila")

    def test_no_match(self):
        self.assertIsNone(match_name("Barcelona", ["Real Madrid", "Sevilla"]))


class CanonicalGroupTests(TestCase):
    def test_group_ids_bidirectional(self):
        league = make_league()
        live = make_team(league, name="Arsenal FC", external_id="57")
        alias = make_team(league, name="Arsenal", external_id="fduk-arsenal")
        alias.canonical = live
        alias.save()
        self.assertEqual(live.canonical_group_ids(), {live.id, alias.id})
        self.assertEqual(alias.canonical_group_ids(), {live.id, alias.id})


class LinkTeamsCommandTests(TestCase):
    def test_links_history_to_live_by_country(self):
        live_league = make_league(name="Premier League", external_id="PL", country="England")
        hist_league = make_league(
            name="Premier League (history)", external_id="fduk-E0",
            country="England", is_active=False,
        )
        live = make_team(live_league, name="Manchester City FC", external_id="65")
        hist = make_team(hist_league, name="Man City", external_id="fduk-man-city")

        call_command("link_teams")
        hist.refresh_from_db()
        self.assertEqual(hist.canonical_id, live.id)


class LinkedHistoryFeatureTests(TestCase):
    def setUp(self):
        self.live_league = make_league(name="Premier League", external_id="PL", country="England")
        self.hist_league = make_league(
            name="Premier League (history)", external_id="fduk-E0",
            country="England", is_active=False,
        )
        self.live_home = make_team(self.live_league, name="Arsenal FC", external_id="57")
        self.live_away = make_team(self.live_league, name="Chelsea FC", external_id="61")
        self.hist_home = make_team(self.hist_league, name="Arsenal", external_id="fduk-arsenal")
        self.hist_opp = make_team(self.hist_league, name="Spurs", external_id="fduk-spurs")
        # Three historical wins for the (historical) Arsenal row.
        for i in range(3):
            make_match(
                self.hist_league, self.hist_home, self.hist_opp, external_id=f"h{i}",
                status=MatchStatus.FINISHED, home_score=2, away_score=0,
                kickoff=timezone.now() - timedelta(days=10 + i),
            )
        self.upcoming = make_match(
            self.live_league, self.live_home, self.live_away, external_id="up",
            status=MatchStatus.SCHEDULED, kickoff=timezone.now() + timedelta(days=1),
        )

    def test_history_ignored_without_link(self):
        feats = get_features(self.upcoming.id)
        self.assertEqual(feats["home_form_pts"], 0)

    def test_history_used_after_link(self):
        self.hist_home.canonical = self.live_home
        self.hist_home.save()
        feats = get_features(self.upcoming.id)
        self.assertEqual(feats["home_form_pts"], 9)  # 3 wins * 3 pts
        self.assertEqual(feats["home_goals_scored_avg"], 2.0)
