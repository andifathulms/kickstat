"""Link historical (football-data.co.uk) team rows to live (football-data.org)
teams so match history is unified for feature engineering.

    python manage.py link_teams            # apply links
    python manage.py link_teams --dry-run  # preview, change nothing

For each active live league it matches its teams to historical teams from the
same country (across all that country's divisions, so promoted/relegated clubs
keep their full history) and sets historical_team.canonical = live_team.
"""
from collections import defaultdict

from django.core.management.base import BaseCommand

from apps.leagues.models import League, Source, Team
from apps.leagues.team_matching import match_name, normalize


class Command(BaseCommand):
    help = "Match football-data.co.uk historical teams to live football-data.org teams."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Preview without saving links."
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]

        # Historical club-data leagues (football-data.co.uk + Understat). Exclude
        # StatsBomb, whose competitions include national teams that would
        # false-match domestic clubs.
        hist_teams = (
            Team.objects.filter(league__is_active=False)
            .exclude(league__external_id__startswith="sb-")
            .select_related("league")
        )
        by_country = defaultdict(list)
        for t in hist_teams:
            by_country[t.league.country].append(t)

        total_links = 0
        live_leagues = League.objects.filter(
            source=Source.FOOTBALL_DATA, is_active=True
        )
        for live_league in live_leagues:
            candidates = by_country.get(live_league.country, [])
            if not candidates:
                continue
            cand_names = [c.name for c in candidates]
            matched, unmatched = 0, []
            live_teams = list(live_league.teams.all())
            for live in live_teams:
                best = match_name(live.name, cand_names)
                if not best:
                    unmatched.append(live.name)
                    continue
                target_norm = normalize(best)
                linked = 0
                for c in candidates:
                    if c.canonical_id:  # first match wins
                        continue
                    if normalize(c.name) == target_norm:
                        if not dry:
                            c.canonical = live
                            c.save(update_fields=["canonical", "updated_at"])
                        linked += 1
                if linked:
                    matched += 1
                    total_links += linked
            self.stdout.write(
                f"{live_league.name}: matched {matched}/{len(live_teams)} teams"
                + (f" — unmatched: {', '.join(unmatched)}" if unmatched else "")
            )

        verb = "Would link" if dry else "Linked"
        self.stdout.write(
            self.style.SUCCESS(f"{verb} {total_links} historical team rows.")
        )
