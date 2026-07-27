"""Repair names already stored with feed-specific escaping.

    python manage.py sanitize_names --dry-run
    python manage.py sanitize_names

The ingest commands now run every name through ``clean_name``, but rows written
before that landed still carry the raw escaping — "Gary O''Neil" from
StatsBomb, "Matt O&#039;Riley" from Understat. No network access needed.
"""
from django.core.management.base import BaseCommand

from apps.common.names import clean_name
from apps.leagues.models import Coach, Player
from apps.matches.models import Referee, Stadium

MODELS = (Player, Coach, Referee, Stadium)


class Command(BaseCommand):
    help = "Rewrite stored names through clean_name."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        total = 0
        for model in MODELS:
            fixed = self._sanitize(model, dry_run)
            total += fixed
            self.stdout.write(f"{model.__name__}: {fixed}")
        verb = "would repair" if dry_run else "repaired"
        self.stdout.write(self.style.SUCCESS(f"{verb} {total} names."))

    def _sanitize(self, model, dry_run):
        fields = ["name"]
        if hasattr(model, "nickname"):
            fields.append("nickname")

        fixed = 0
        for row in model.objects.iterator(chunk_size=500):
            changed = []
            for field in fields:
                value = getattr(row, field)
                cleaned = clean_name(value)
                if cleaned != value:
                    setattr(row, field, cleaned)
                    changed.append(field)
            if not changed:
                continue
            fixed += 1
            if dry_run:
                self.stdout.write(f"  {model.__name__} {row.pk}: {row.name}")
            else:
                row.save(update_fields=changed + ["updated_at"])
        return fixed
