"""Populate Referee / Stadium / Coach FKs from each match's stored raw_data.

    python manage.py backfill_match_people

No network: StatsBomb match metadata (referee, stadium, managers) is already in
Match.raw_data, so this rebuilds the normalised people without re-ingesting.
"""
from django.core.management.base import BaseCommand

from apps.matches.models import Match
from apps.predictions.management.commands.ingest_statsbomb import (
    Command as Ingest,
)


class Command(BaseCommand):
    help = "Backfill referee/stadium/coach FKs from Match.raw_data."

    def handle(self, *args, **options):
        ing = Ingest()
        qs = Match.objects.filter(external_id__startswith="sb-")
        total = qs.count()
        updated = 0
        for match in qs.iterator(chunk_size=500):
            raw = match.raw_data or {}
            ref = ing._referee(raw.get("referee"))
            stad = ing._stadium(raw.get("stadium"))
            home = ing._coach((raw.get("home_team") or {}).get("managers"))
            away = ing._coach((raw.get("away_team") or {}).get("managers"))
            Match.objects.filter(pk=match.pk).update(
                referee=ref, stadium=stad, home_coach=home, away_coach=away
            )
            updated += 1
            if updated % 500 == 0:
                self.stdout.write(f"  {updated}/{total}")
        self.stdout.write(
            self.style.SUCCESS(f"Backfilled {updated} matches.")
        )
