from django.core.management import call_command
from django.test import TestCase

from apps.common.names import clean_name
from apps.leagues.models import Coach, Player
from apps.matches.models import Referee, Stadium


class CleanNameTests(TestCase):
    def test_undoes_sql_escaped_apostrophes(self):
        self.assertEqual(clean_name("Gary O''Neil"), "Gary O'Neil")
        self.assertEqual(clean_name("Stade de l''Aube"), "Stade de l'Aube")

    def test_undoes_html_escaped_apostrophes(self):
        self.assertEqual(clean_name("Matt O&#039;Riley"), "Matt O'Riley")

    def test_leaves_clean_names_alone(self):
        for name in ("Erling Haaland", "Dara O'Shea", "Nott'm Forest", ""):
            self.assertEqual(clean_name(name), name)

    def test_passes_non_strings_through(self):
        self.assertIsNone(clean_name(None))


class SanitizeNamesCommandTests(TestCase):
    def setUp(self):
        self.player = Player.objects.create(
            name="Gary O''Neil", nickname="O''Neil", external_id="sb-1"
        )
        self.coach = Coach.objects.create(name="David O''Leary", external_id="sb-2")
        self.referee = Referee.objects.create(name="Matt O&#039;Riley", external_id="x")
        self.stadium = Stadium.objects.create(name="Levi''s Stadium", external_id="y")
        self.clean = Player.objects.create(name="Erling Haaland", external_id="sb-3")

    def test_repairs_every_model(self):
        call_command("sanitize_names")
        self.player.refresh_from_db()
        self.coach.refresh_from_db()
        self.referee.refresh_from_db()
        self.stadium.refresh_from_db()
        self.assertEqual(self.player.name, "Gary O'Neil")
        self.assertEqual(self.player.nickname, "O'Neil")
        self.assertEqual(self.coach.name, "David O'Leary")
        self.assertEqual(self.referee.name, "Matt O'Riley")
        self.assertEqual(self.stadium.name, "Levi's Stadium")

    def test_dry_run_writes_nothing(self):
        call_command("sanitize_names", "--dry-run")
        self.player.refresh_from_db()
        self.assertEqual(self.player.name, "Gary O''Neil")

    def test_leaves_already_clean_rows_untouched(self):
        before = self.clean.updated_at
        call_command("sanitize_names")
        self.clean.refresh_from_db()
        self.assertEqual(self.clean.updated_at, before)
