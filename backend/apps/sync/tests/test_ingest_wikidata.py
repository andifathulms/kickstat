from datetime import datetime, timezone
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.leagues.models import Coach, League, Source, Team
from apps.matches.models import Match, MatchStatus, Stadium
from apps.sync.management.commands import ingest_wikidata as cmd

ARSENAL = cmd.DIVISION_CLUBS["E0"]["Arsenal"]
SPURS = cmd.DIVISION_CLUBS["E0"]["Tottenham"]


def binding(**kwargs):
    return {k: {"value": v} for k, v in kwargs.items() if v is not None}


VENUES = [
    binding(
        club=f"http://www.wikidata.org/entity/{ARSENAL}",
        venue="http://www.wikidata.org/entity/Q189476",
        venueLabel="Arsenal Stadium",
        countryLabel="United Kingdom",
        start="1913-09-06T00:00:00Z",
        end="2006-05-07T00:00:00Z",
    ),
    binding(
        club=f"http://www.wikidata.org/entity/{ARSENAL}",
        venue="http://www.wikidata.org/entity/Q189474",
        venueLabel="Emirates Stadium",
        countryLabel="United Kingdom",
        start="2006-07-22T00:00:00Z",
    ),
    binding(
        club=f"http://www.wikidata.org/entity/{SPURS}",
        venue="http://www.wikidata.org/entity/Q737117",
        venueLabel="White Hart Lane",
        start="1899-09-04T00:00:00Z",
        end="2017-05-14T00:00:00Z",
    ),
]

COACHES = [
    # A dual national: SPARQL repeats the spell once per citizenship, and only
    # the second row carries the date of birth.
    binding(
        club=f"http://www.wikidata.org/entity/{SPURS}",
        coach="http://www.wikidata.org/entity/Q315636",
        coachLabel="Ange Postecoglou",
        nationalityLabel="Greece",
        start="2023-07-01T00:00:00Z",
        end="2025-06-06T00:00:00Z",
    ),
    binding(
        club=f"http://www.wikidata.org/entity/{SPURS}",
        coach="http://www.wikidata.org/entity/Q315636",
        coachLabel="Ange Postecoglou",
        nationalityLabel="Australia",
        dob="1965-08-27T00:00:00Z",
        start="2023-07-01T00:00:00Z",
        end="2025-06-06T00:00:00Z",
    ),
    # A caretaker spell nested inside a longer record.
    binding(
        club=f"http://www.wikidata.org/entity/{ARSENAL}",
        coachLabel="Arsene Wenger",
        coach="http://www.wikidata.org/entity/Q170371",
        start="1996-10-01T00:00:00Z",
        end="2018-05-13T00:00:00Z",
    ),
    binding(
        club=f"http://www.wikidata.org/entity/{ARSENAL}",
        coachLabel="Pat Rice",
        coach="http://www.wikidata.org/entity/Q1249999",
        start="2005-01-01T00:00:00Z",
        end="2005-03-01T00:00:00Z",
    ),
]


class FakeClient:
    def __init__(self, venues=VENUES, coaches=COACHES):
        self.payloads = [venues, coaches]

    def query(self, sparql):
        return self.payloads.pop(0)


def run(*args, client=None):
    client = client or FakeClient()
    with mock.patch.object(cmd, "WikidataClient", return_value=client), \
            mock.patch.object(cmd.time, "sleep"):
        call_command("ingest_wikidata", *args)
    return client


class IntervalTests(TestCase):
    def test_open_ended_spell_covers_later_dates(self):
        i = cmd.Interval("x", datetime(2006, 7, 22, tzinfo=timezone.utc), None)
        self.assertTrue(i.covers(datetime(2020, 1, 1, tzinfo=timezone.utc)))
        self.assertFalse(i.covers(datetime(2005, 1, 1, tzinfo=timezone.utc)))

    def test_pick_prefers_the_narrower_overlapping_spell(self):
        long = cmd.Interval(
            "wenger",
            datetime(1996, 10, 1, tzinfo=timezone.utc),
            datetime(2018, 5, 13, tzinfo=timezone.utc),
        )
        caretaker = cmd.Interval(
            "rice",
            datetime(2005, 1, 1, tzinfo=timezone.utc),
            datetime(2005, 3, 1, tzinfo=timezone.utc),
        )
        obj, ambiguous = cmd.pick(
            [long, caretaker], datetime(2005, 2, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(obj, "rice")
        self.assertTrue(ambiguous)

    def test_pick_returns_none_when_nothing_covers(self):
        i = cmd.Interval("x", None, datetime(2000, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(
            cmd.pick([i], datetime(2020, 1, 1, tzinfo=timezone.utc)), (None, False)
        )

    def test_parse_date_rejects_imprecise_values(self):
        self.assertIsNone(cmd.parse_date("2005-00-00T00:00:00Z"))
        self.assertIsNone(cmd.parse_date(""))


class BackfillTests(TestCase):
    def setUp(self):
        self.league = League.objects.create(
            source=Source.FOOTBALL_DATA,
            external_id="fduk-E0",
            name="Premier League (history)",
            country="England",
        )
        self.arsenal = Team.objects.create(
            source=Source.FOOTBALL_DATA, external_id="fduk-arsenal",
            name="Arsenal", league=self.league,
        )
        self.spurs = Team.objects.create(
            source=Source.FOOTBALL_DATA, external_id="fduk-tottenham",
            name="Tottenham", league=self.league,
        )

    def match(self, when, home=None, away=None, **kwargs):
        return Match.objects.create(
            external_id=f"m-{when.date()}-{kwargs.get('tag', '')}",
            league=self.league,
            home_team=home or self.arsenal,
            away_team=away or self.spurs,
            kickoff=when,
            status=MatchStatus.FINISHED,
        )

    def test_venue_resolves_as_of_kickoff(self):
        old = self.match(datetime(2005, 3, 5, tzinfo=timezone.utc), tag="a")
        new = self.match(datetime(2010, 3, 5, tzinfo=timezone.utc), tag="b")
        run("--division", "E0")
        old.refresh_from_db()
        new.refresh_from_db()
        self.assertEqual(old.stadium.name, "Arsenal Stadium")
        self.assertEqual(new.stadium.name, "Emirates Stadium")

    def test_gap_between_venues_is_left_null(self):
        # Arsenal's spells end 2006-05-07 and resume 2006-07-22.
        gap = self.match(datetime(2006, 6, 1, tzinfo=timezone.utc), tag="gap")
        run("--division", "E0")
        gap.refresh_from_db()
        self.assertIsNone(gap.stadium)

    def test_coach_resolved_per_side(self):
        m = self.match(datetime(2024, 3, 5, tzinfo=timezone.utc), tag="c")
        run("--division", "E0")
        m.refresh_from_db()
        self.assertEqual(m.away_coach.name, "Ange Postecoglou")
        # Attributes merged across both citizenship rows, nationality picked
        # deterministically; one spell, not one per citizenship.
        self.assertEqual(m.away_coach.nationality, "Australia")
        self.assertEqual(str(m.away_coach.date_of_birth), "1965-08-27")
        self.assertEqual(Coach.objects.filter(name="Ange Postecoglou").count(), 1)
        # Wenger's spell had ended by 2024.
        self.assertIsNone(m.home_coach)

    def test_caretaker_wins_over_the_enclosing_spell(self):
        m = self.match(datetime(2005, 2, 1, tzinfo=timezone.utc), tag="d")
        run("--division", "E0")
        m.refresh_from_db()
        self.assertEqual(m.home_coach.name, "Pat Rice")

    def test_creates_no_leagues_teams_or_matches(self):
        self.match(datetime(2010, 3, 5, tzinfo=timezone.utc), tag="e")
        run("--division", "E0")
        self.assertEqual(League.objects.count(), 1)
        self.assertEqual(Team.objects.count(), 2)
        self.assertEqual(Match.objects.count(), 1)

    def test_idempotent(self):
        self.match(datetime(2010, 3, 5, tzinfo=timezone.utc), tag="f")
        run("--division", "E0")
        before = (Stadium.objects.count(), Coach.objects.count())
        run("--division", "E0")
        self.assertEqual((Stadium.objects.count(), Coach.objects.count()), before)

    def test_dry_run_writes_nothing(self):
        m = self.match(datetime(2010, 3, 5, tzinfo=timezone.utc), tag="g")
        run("--division", "E0", "--dry-run")
        m.refresh_from_db()
        self.assertIsNone(m.stadium)
        self.assertEqual(Stadium.objects.count(), 0)
        self.assertEqual(Coach.objects.count(), 0)

    def test_existing_values_kept_unless_refresh(self):
        m = self.match(datetime(2010, 3, 5, tzinfo=timezone.utc), tag="h")
        keep = Stadium.objects.create(name="Manually Set", external_id="manual")
        m.stadium = keep
        m.save(update_fields=["stadium"])

        run("--division", "E0")
        m.refresh_from_db()
        self.assertEqual(m.stadium, keep)

        run("--division", "E0", "--refresh")
        m.refresh_from_db()
        self.assertEqual(m.stadium.name, "Emirates Stadium")

    def test_unknown_division_errors(self):
        with self.assertRaises(CommandError):
            run("--division", "ZZ")

    def test_missing_history_league_errors(self):
        League.objects.all().delete()
        with self.assertRaises(CommandError):
            run("--division", "E0")
