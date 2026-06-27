from unittest import mock

from django.core.cache import cache
from django.test import TestCase

from apps.sync import client
from apps.sync.models import SyncLog


class SyncLoggerTests(TestCase):
    def test_records_counts_and_success(self):
        with client.sync_logger("demo", target="PL") as counters:
            counters["created"] += 2
            counters["updated"] += 1
        log = SyncLog.objects.get()
        self.assertTrue(log.success)
        self.assertEqual(log.records_created, 2)
        self.assertEqual(log.records_updated, 1)
        self.assertEqual(log.target, "PL")

    def test_records_failure_and_reraises(self):
        with self.assertRaises(ValueError):
            with client.sync_logger("demo"):
                raise ValueError("boom")
        log = SyncLog.objects.get()
        self.assertFalse(log.success)
        self.assertIn("boom", log.errors)


class ApiFootballQuotaTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_aborts_when_quota_reached(self):
        cache.set(client.API_FOOTBALL_COUNTER_KEY, client.API_FOOTBALL_DAILY_CAP)
        with self.assertRaises(RuntimeError):
            client.api_football_get("fixtures")

    def test_increments_counter_on_success(self):
        fake = mock.Mock()
        fake.json.return_value = {"response": []}
        fake.raise_for_status.return_value = None
        with mock.patch("apps.sync.client.requests.get", return_value=fake):
            client.api_football_get("fixtures")
        self.assertEqual(cache.get(client.API_FOOTBALL_COUNTER_KEY), 1)
