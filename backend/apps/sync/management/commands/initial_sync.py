"""Bootstrap command: run all sync tasks once, sequentially.

    python manage.py initial_sync

Runs synchronously (not via Celery) so a fresh clone can be populated in one
shot. football-data.org tasks self-throttle (6s/request).
"""
from django.core.management.base import BaseCommand

from apps.leagues.models import League, Source
from apps.sync.tasks import api_football, football_data


class Command(BaseCommand):
    help = "Run all sync tasks once sequentially to bootstrap the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-liga1",
            action="store_true",
            help="Skip API-Football Liga 1 sync (conserve the 100 req/day quota).",
        )

    def handle(self, *args, **options):
        self.stdout.write("1/4 Syncing leagues...")
        football_data.sync_leagues.apply()

        league_ids = list(
            League.objects.filter(
                source=Source.FOOTBALL_DATA, is_active=True
            ).values_list("id", flat=True)
        )
        self.stdout.write(f"Found {len(league_ids)} football-data.org leagues.")

        for lid in league_ids:
            league = League.objects.get(pk=lid)
            self.stdout.write(f"2/4 Standings: {league.name}")
            football_data.sync_standings.apply(args=[lid])
            self.stdout.write(f"3/4 Fixtures: {league.name}")
            football_data.sync_fixtures.apply(args=[lid])
            self.stdout.write(f"3/4 Results: {league.name}")
            football_data.sync_results.apply(args=[lid])

        if not options["skip_liga1"]:
            self.stdout.write("4/4 Liga 1 fixtures (API-Football)...")
            api_football.sync_liga1_fixtures.apply()

        self.stdout.write(self.style.SUCCESS("Initial sync complete."))
