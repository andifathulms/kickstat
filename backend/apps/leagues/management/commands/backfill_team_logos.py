"""Copy crest URLs onto logo-less teams (e.g. StatsBomb rows) by matching
normalized team names against teams that already have a logo.

    python manage.py backfill_team_logos
"""
from django.core.management.base import BaseCommand

from apps.leagues.models import Team
from apps.leagues.team_matching import normalize


class Command(BaseCommand):
    help = "Backfill team logo_url by normalized-name match."

    def handle(self, *args, **options):
        # name -> logo, from teams that already have one
        logos: dict[str, str] = {}
        for t in Team.objects.exclude(logo_url="").values_list("name", "logo_url"):
            logos.setdefault(normalize(t[0]), t[1])

        updated = 0
        missing = Team.objects.filter(logo_url="")
        for team in missing.iterator(chunk_size=500):
            url = logos.get(normalize(team.name))
            if url:
                Team.objects.filter(pk=team.pk).update(logo_url=url)
                updated += 1
        self.stdout.write(
            self.style.SUCCESS(f"Backfilled {updated} team logos.")
        )
