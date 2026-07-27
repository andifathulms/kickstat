from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from apps.leagues.models import League, Source, Team
from apps.matches.models import Match, MatchStats, MatchStatus
from apps.sync.management.commands import ingest_football_data_uk as cmd

CSV = (
    "Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,"
    "HS,AS,HST,AST,HC,AC,HF,AF,HY,AY,HR,AR\n"
    "E0,12/08/2023,15:00,Arsenal,Chelsea,2,1,H,"
    "14,7,6,3,8,4,11,13,1,2,0,1\n"
    "E0,13/08/2023,17:30,Liverpool,Man City,1,1,D,"
    "10,12,4,5,5,6,9,8,2,1,0,0\n"
)


def _fake_response(text, status=200):
    fake = mock.Mock()
    fake.status_code = status
    fake.content = text.encode("latin-1")
    return fake


class IngestFootballDataUkTests(TestCase):
    @mock.patch(
        "apps.sync.management.commands.ingest_football_data_uk.requests.get"
    )
    def test_creates_matches_and_stats(self, mocked_get):
        mocked_get.return_value = _fake_response(CSV)
        call_command("ingest_football_data_uk", "--division", "E0", "--season", "2324")

        league = League.objects.get(external_id="fduk-E0", source=Source.FOOTBALL_DATA)
        self.assertFalse(league.is_active)
        self.assertEqual(Match.objects.count(), 2)
        self.assertEqual(Team.objects.count(), 4)

        m = Match.objects.get(home_team__name="Arsenal")
        self.assertEqual(m.status, MatchStatus.FINISHED)
        self.assertEqual((m.home_score, m.away_score), (2, 1))
        stats = MatchStats.objects.get(match=m)
        self.assertEqual(stats.home_shots, 14)
        self.assertEqual(stats.away_shots_on_target, 3)
        self.assertEqual(stats.home_red_cards, 0)
        self.assertEqual(stats.away_red_cards, 1)

    @mock.patch(
        "apps.sync.management.commands.ingest_football_data_uk.requests.get"
    )
    def test_idempotent(self, mocked_get):
        mocked_get.return_value = _fake_response(CSV)
        call_command("ingest_football_data_uk", "--division", "E0", "--season", "2324")
        mocked_get.return_value = _fake_response(CSV)
        call_command("ingest_football_data_uk", "--division", "E0", "--season", "2324")
        self.assertEqual(Match.objects.count(), 2)
        self.assertEqual(MatchStats.objects.count(), 2)

    @mock.patch(
        "apps.sync.management.commands.ingest_football_data_uk.requests.get"
    )
    def test_missing_season_skipped(self, mocked_get):
        mocked_get.return_value = _fake_response("", status=404)
        call_command("ingest_football_data_uk", "--division", "E0", "--season", "9999")
        self.assertEqual(Match.objects.count(), 0)


class FetchCsvTests(TestCase):
    def test_accepts_a_real_csv_with_or_without_a_bom(self):
        self.assertTrue(cmd.looks_like_csv("Div,Date,HomeTeam\nE0,01/01/24,Arsenal"))
        self.assertTrue(cmd.looks_like_csv("﻿Div,Date,HomeTeam"))

    def test_accepts_a_utf8_bom_decoded_as_latin1(self):
        # How the BOM actually arrives: these files are decoded as latin-1, so
        # the three BOM bytes become "ï»¿" rather than U+FEFF.
        raw = "Div,Date,HomeTeam".encode("utf-8-sig")
        self.assertEqual(raw[:3], b"\xef\xbb\xbf")
        self.assertTrue(cmd.looks_like_csv(raw.decode("latin-1")))

    def test_rejects_an_intercepted_html_response(self):
        # ISP filtering portals answer with HTML that parses as a zero-row CSV.
        self.assertFalse(cmd.looks_like_csv("<html><body>blocked</body></html>"))
        self.assertFalse(cmd.looks_like_csv(""))
        self.assertFalse(cmd.looks_like_csv(None))

    def test_retries_past_an_intercepted_response(self):
        good = "Div,Date,HomeTeam\nE0,01/01/24,Arsenal"
        responses = [
            mock.Mock(status_code=200, content=b"<html>blocked</html>"),
            mock.Mock(status_code=200, content=good.encode("latin-1")),
        ]
        with mock.patch.object(cmd.requests, "get", side_effect=responses), \
                mock.patch.object(cmd.time, "sleep"):
            self.assertEqual(cmd.fetch_csv("http://x/E0.csv"), good)

    def test_gives_up_when_every_attempt_is_intercepted(self):
        blocked = mock.Mock(status_code=200, content=b"<html>blocked</html>")
        with mock.patch.object(cmd.requests, "get", return_value=blocked), \
                mock.patch.object(cmd.time, "sleep"):
            self.assertIsNone(cmd.fetch_csv("http://x/E0.csv"))
