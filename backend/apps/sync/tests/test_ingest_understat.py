import json
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from apps.leagues.models import League, Source
from apps.matches.models import Match, MatchStats
from apps.sync.management.commands import ingest_understat as cmd

ENTRIES = [
    {
        "id": "1001",
        "isResult": True,
        "h": {"id": "88", "title": "Manchester City", "short_title": "MCI"},
        "a": {"id": "89", "title": "Manchester United", "short_title": "MUN"},
        "goals": {"h": "3", "a": "1"},
        "xG": {"h": "2.41", "a": "0.77"},
        "datetime": "2023-10-29 15:30:00",
    },
    {
        "id": "1002",
        "isResult": False,  # upcoming -> skipped
        "h": {"id": "88", "title": "Manchester City", "short_title": "MCI"},
        "a": {"id": "90", "title": "Arsenal", "short_title": "ARS"},
        "goals": {"h": "0", "a": "0"},
        "xG": {"h": "0", "a": "0"},
        "datetime": "2099-01-01 15:30:00",
    },
]


class DecodeDatesDataTests(TestCase):
    def test_decodes_hex_escaped_blob(self):
        js = json.dumps(ENTRIES)
        escaped = "".join("\\x%02x" % b for b in js.encode("utf-8"))
        html = f"<script>var datesData = JSON.parse('{escaped}');</script>"
        result = cmd.decode_dates_data(html)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["h"]["title"], "Manchester City")

    def test_no_blob_returns_empty(self):
        self.assertEqual(cmd.decode_dates_data("<html></html>"), [])


class IngestUnderstatTests(TestCase):
    @mock.patch(
        "apps.sync.management.commands.ingest_understat.fetch_dates_data",
        return_value=ENTRIES,
    )
    def test_ingests_results_with_xg(self, _mock):
        call_command("ingest_understat", "--league", "EPL", "--season", "2023")
        league = League.objects.get(
            source=Source.FOOTBALL_DATA, external_id="understat-EPL-2023"
        )
        self.assertEqual(league.country, "England")
        # only the finished match is ingested
        self.assertEqual(Match.objects.count(), 1)
        stats = MatchStats.objects.get()
        self.assertEqual(stats.home_xg, 2.41)
        self.assertEqual(stats.away_xg, 0.77)

    @mock.patch(
        "apps.sync.management.commands.ingest_understat.fetch_dates_data",
        return_value=ENTRIES,
    )
    def test_idempotent(self, _mock):
        call_command("ingest_understat", "--league", "EPL", "--season", "2023")
        call_command("ingest_understat", "--league", "EPL", "--season", "2023")
        self.assertEqual(Match.objects.count(), 1)
