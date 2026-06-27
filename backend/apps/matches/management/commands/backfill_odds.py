"""Backfill MatchOdds from the betting-odds columns already stored in each
football-data.co.uk match's ``raw_data`` (no new downloads required).

    python manage.py backfill_odds

football-data.co.uk ships ~1X2 and over/under odds per match. We take the market
average where available, falling back through Betbrain average, Bet365, Pinnacle,
and William Hill so coverage spans 2005-present (column names changed over time).
"""
from django.core.management.base import BaseCommand

from apps.matches.models import Match, MatchOdds


def _f(row, *keys):
    for k in keys:
        v = row.get(k)
        if v in (None, "", "NA"):
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


def extract_odds(raw: dict):
    """Return (home, draw, away, over25, under25) decimal odds from a raw row."""
    home = _f(raw, "AvgH", "BbAvH", "B365H", "PSH", "WHH")
    draw = _f(raw, "AvgD", "BbAvD", "B365D", "PSD", "WHD")
    away = _f(raw, "AvgA", "BbAvA", "B365A", "PSA", "WHA")
    over = _f(raw, "Avg>2.5", "BbAv>2.5", "B365>2.5", "P>2.5", "GB>2.5")
    under = _f(raw, "Avg<2.5", "BbAv<2.5", "B365<2.5", "P<2.5", "GB<2.5")
    return home, draw, away, over, under


class Command(BaseCommand):
    help = "Populate MatchOdds from odds stored in football-data.co.uk raw_data."

    def add_arguments(self, parser):
        parser.add_argument("--batch", type=int, default=2000)

    def handle(self, *args, **options):
        batch_size = options["batch"]
        qs = (
            Match.objects.filter(external_id__startswith="fduk-", odds__isnull=True)
            .only("id", "raw_data")
            .iterator(chunk_size=batch_size)
        )
        buffer, created, skipped = [], 0, 0
        for match in qs:
            home, draw, away, over, under = extract_odds(match.raw_data or {})
            if not any([home, draw, away, over, under]):
                skipped += 1
                continue
            buffer.append(
                MatchOdds(
                    match=match,
                    home_odds=home,
                    draw_odds=draw,
                    away_odds=away,
                    over25_odds=over,
                    under25_odds=under,
                )
            )
            if len(buffer) >= batch_size:
                MatchOdds.objects.bulk_create(buffer, ignore_conflicts=True)
                created += len(buffer)
                buffer = []
                self.stdout.write(f"  {created} created...")
        if buffer:
            MatchOdds.objects.bulk_create(buffer, ignore_conflicts=True)
            created += len(buffer)
        self.stdout.write(
            self.style.SUCCESS(
                f"Backfilled {created} odds rows ({skipped} matches had no odds)."
            )
        )
