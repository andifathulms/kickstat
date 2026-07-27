"""Backfill match venues and managers from Wikidata.

    python manage.py ingest_wikidata --division E0 --dry-run
    python manage.py ingest_wikidata --division E0

football-data.co.uk gives us a referee but no venue and no manager, and
Understat has neither. Wikidata records both as time-qualified statements —
a club's home ground (P115) and its head coaches (P286) each carry start
(P580) and end (P582) dates — so both can be resolved *as of a match's
kickoff* rather than assumed constant. That matters over a 20-season history:
Arsenal left Highbury in 2006, West Ham left Upton Park in 2016, Spurs left
White Hart Lane in 2017.

Wikidata is CC0 and exposes a real SPARQL endpoint, so this is a query rather
than a scrape.

Backfill-only by design, like ingest_understat: it creates Stadium and Coach
rows and points existing matches at them, but never creates a League, Team or
Match, and it fills a match only when exactly one venue or reign covers the
kickoff. Ambiguous and uncovered matches are left null and reported — a blank
manager is better than a wrong one.
"""
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests
from django.core.management.base import BaseCommand, CommandError

from apps.common.names import clean_name
from apps.leagues.models import Coach, League, Source, Team
from apps.matches.models import Match, Stadium

ENDPOINT = "https://query.wikidata.org/sparql"
# Wikidata asks that clients identify themselves and stay under ~1 query/sec.
USER_AGENT = "kickstat/1.0 (football analytics; data ingest)"
REQUEST_DELAY_SECONDS = 1.0
MAX_RETRIES = 3

# football-data.co.uk club name -> Wikidata QID, for every club appearing in
# the division's history. Resolved by exact English label against "association
# football club", disambiguating namesakes (defunct Victorian clubs sharing a
# name) by requiring a home venue. Baked in rather than resolved at runtime:
# QIDs are stable identifiers, and a silent mismatch here would attribute a
# manager to the wrong club.
DIVISION_CLUBS = {
    "E0": {
        "Arsenal": "Q9617",
        "Aston Villa": "Q18711",
        "Birmingham": "Q19444",
        "Blackburn": "Q19446",
        "Blackpool": "Q19449",
        "Bolton": "Q19451",
        "Bournemouth": "Q19568",
        "Brentford": "Q19571",
        "Brighton": "Q19453",
        "Burnley": "Q19458",
        "Cardiff": "Q18662",
        "Charlton": "Q19462",
        "Chelsea": "Q9616",
        "Crystal Palace": "Q19467",
        "Derby": "Q19470",
        "Everton": "Q5794",
        "Fulham": "Q18708",
        "Huddersfield": "Q19473",
        "Hull": "Q19477",
        "Ipswich": "Q9653",
        "Leeds": "Q1128631",
        "Leicester": "Q19481",
        "Liverpool": "Q1130849",
        "Luton": "Q18520",
        "Man City": "Q50602",
        "Man United": "Q18656",
        "Middlesbrough": "Q18661",
        "Newcastle": "Q18716",
        "Norwich": "Q18721",
        "Nott'm Forest": "Q19490",
        "Portsmouth": "Q19604",
        "QPR": "Q18723",
        "Reading": "Q18729",
        "Sheffield United": "Q19607",
        "Southampton": "Q18732",
        "Stoke": "Q18736",
        "Sunderland": "Q18739",
        "Swansea": "Q18659",
        "Tottenham": "Q18741",
        "Watford": "Q2714",
        "West Brom": "Q18744",
        "West Ham": "Q18747",
        "Wigan": "Q18750",
        "Wolves": "Q19500",
    },
    "SP1": {
        "Alaves": "Q223620",
        "Almeria": "Q10407",
        "Ath Bilbao": "Q8687",
        "Ath Madrid": "Q8701",
        "Barcelona": "Q7156",
        "Betis": "Q8723",
        "Cadiz": "Q460448",
        "Celta": "Q8749",
        "Cordoba": "Q10499",
        "Eibar": "Q770740",
        "Elche": "Q10512",
        "Espanol": "Q8780",
        "Getafe": "Q8806",
        "Gimnastic": "Q257984",
        "Girona": "Q11945",
        "Granada": "Q8812",
        "Hercules": "Q11963",
        "Huesca": "Q11971",
        "La Coruna": "Q8760",
        "Las Palmas": "Q11979",
        "Leganes": "Q856119",
        "Levante": "Q8823",
        "Malaga": "Q8857",
        "Mallorca": "Q8835",
        "Murcia": "Q12230",
        "Numancia": "Q12158",
        "Osasuna": "Q10286",
        "Oviedo": "Q271574",
        "Real Madrid": "Q8682",
        "Recreativo": "Q12249",
        "Santander": "Q12236",
        "Sevilla": "Q10329",
        "Sociedad": "Q10315",
        "Sp Gijon": "Q12278",
        "Tenerife": "Q216661",
        "Valencia": "Q10333",
        "Valladolid": "Q10319",
        "Vallecano": "Q10300",
        "Villarreal": "Q12297",
        "Xerez": "Q12308",
        "Zaragoza": "Q10308",
    },
    "D1": {
        "Aachen": "Q153535",
        "Augsburg": "Q15755",
        "Bayern Munich": "Q15789",
        "Bielefeld": "Q105844",
        "Bochum": "Q105861",
        "Braunschweig": "Q154053",
        "Cottbus": "Q107818",
        "Darmstadt": "Q479351",
        "Dortmund": "Q41420",
        "Duisburg": "Q154293",
        "Ein Frankfurt": "Q38245",
        "FC Koln": "Q104770",
        "Fortuna Dusseldorf": "Q151747",
        "Freiburg": "Q106394",
        "Greuther Furth": "Q153539",
        "Hamburg": "Q51974",
        "Hannover": "Q33748",
        "Hansa Rostock": "Q142005",
        "Heidenheim": "Q162251",
        "Hertha": "Q102720",
        "Hoffenheim": "Q22707",
        "Holstein Kiel": "Q157828",
        "Ingolstadt": "Q170117",
        "Kaiserslautern": "Q8466",
        "Karlsruhe": "Q105853",
        "Leverkusen": "Q104761",
        "M'gladbach": "Q101959",
        "Mainz": "Q105254",
        "Nurnberg": "Q15786",
        "Paderborn": "Q160532",
        "RB Leipzig": "Q702455",
        "Schalke 04": "Q32494",
        "St Pauli": "Q6463",
        "Stuttgart": "Q4512",
        "Union Berlin": "Q141971",
        "Werder Bremen": "Q51976",
        "Wolfsburg": "Q101859",
    },
}

VENUE_QUERY = """
SELECT ?club ?venue ?venueLabel ?countryLabel ?start ?end WHERE {
  VALUES ?club { %s }
  ?club p:P115 ?st .
  ?st ps:P115 ?venue .
  OPTIONAL { ?st pq:P580 ?start }
  OPTIONAL { ?st pq:P582 ?end }
  OPTIONAL { ?venue wdt:P17 ?country }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
"""

COACH_QUERY = """
SELECT ?club ?coach ?coachLabel ?nationalityLabel ?dob ?start ?end WHERE {
  VALUES ?club { %s }
  ?club p:P286 ?st .
  ?st ps:P286 ?coach .
  OPTIONAL { ?st pq:P580 ?start }
  OPTIONAL { ?st pq:P582 ?end }
  OPTIONAL { ?coach wdt:P27 ?nationality }
  OPTIONAL { ?coach wdt:P569 ?dob }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
"""


def parse_date(value):
    """Wikidata dates are ISO 8601; imprecise ones use a 00 month or day."""
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def qid_of(uri):
    return uri.rsplit("/", 1)[-1]


class WikidataClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"}
        )

    def query(self, sparql):
        last = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(
                    ENDPOINT, params={"query": sparql}, timeout=120
                )
                resp.raise_for_status()
                return resp.json()["results"]["bindings"]
            except (requests.RequestException, ValueError, KeyError) as exc:
                last = exc
                if attempt < MAX_RETRIES:
                    time.sleep(attempt * 5)
        raise last


class Interval:
    """A venue or managerial spell, with the row it resolves to."""

    def __init__(self, obj, start, end):
        self.obj = obj
        self.start = start
        self.end = end

    def covers(self, when):
        if self.start and when < self.start:
            return False
        if self.end and when > self.end:
            return False
        return True


def pick(intervals, when):
    """The one spell covering ``when``.

    Wikidata often nests a caretaker spell inside a longer record, so when
    several overlap prefer the one that started most recently — the narrower,
    more specific claim. Undated spells cover everything, so they only win
    when nothing else applies.
    """
    hits = [i for i in intervals if i.covers(when)]
    if not hits:
        return None, False
    dated = [i for i in hits if i.start]
    if dated:
        dated.sort(key=lambda i: i.start, reverse=True)
        return dated[0].obj, len(dated) > 1
    return hits[0].obj, len(hits) > 1


class Command(BaseCommand):
    help = "Backfill match stadiums and coaches from Wikidata."

    def add_arguments(self, parser):
        parser.add_argument(
            "--division",
            required=True,
            help=f"football-data.co.uk division code. Known: {', '.join(DIVISION_CLUBS)}",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Report without writing."
        )
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Overwrite stadium/coach values that are already set.",
        )

    def handle(self, *args, **options):
        division = options["division"].upper()
        if division not in DIVISION_CLUBS:
            raise CommandError(
                f"No club map for {division}. Known: {', '.join(DIVISION_CLUBS)}"
            )
        self.dry_run = options["dry_run"]
        self.refresh = options["refresh"]

        league = League.objects.filter(
            source=Source.FOOTBALL_DATA, external_id=f"fduk-{division}"
        ).first()
        if league is None:
            raise CommandError(
                f"No '(history)' league for {division} — run ingest_football_data_uk first."
            )

        teams = self._teams_by_qid(league, division)
        if not teams:
            raise CommandError(f"None of the {division} clubs matched a local team.")
        self.stdout.write(f"{len(teams)} clubs matched")

        client = WikidataClient()
        venues = self._fetch_venues(client, teams)
        time.sleep(REQUEST_DELAY_SECONDS)
        coaches = self._fetch_coaches(client, teams)

        self._backfill(league, teams, venues, coaches)

    # ------------------------------------------------------------- resolution

    def _teams_by_qid(self, league, division):
        """Map QID -> local Team, via the clubs appearing in this league.

        Scoped by matches rather than ``Team.league`` for the same reason as
        ingest_understat: that FK points at whichever division was ingested
        last for clubs that have played in more than one.
        """
        matches = Match.objects.filter(league=league)
        team_ids = set(matches.values_list("home_team_id", flat=True).distinct()) | set(
            matches.values_list("away_team_id", flat=True).distinct()
        )
        by_name = {t.name: t for t in Team.objects.filter(id__in=team_ids)}

        resolved, missing = {}, []
        for name, qid in DIVISION_CLUBS[division].items():
            team = by_name.get(name)
            if team is None:
                missing.append(name)
                continue
            resolved[qid] = team
        unmapped = sorted(set(by_name) - {t.name for t in resolved.values()})
        if missing:
            self.stderr.write(f"  no local team for: {', '.join(sorted(missing))}")
        if unmapped:
            self.stderr.write(f"  no QID for: {', '.join(unmapped)}")
        return resolved

    def _values(self, teams):
        return " ".join(f"wd:{qid}" for qid in teams)

    def _fetch_venues(self, client, teams):
        rows = client.query(VENUE_QUERY % self._values(teams))
        venues = defaultdict(list)
        for row in rows:
            name = clean_name(self._value(row, "venueLabel"))
            if not name:
                continue
            stadium = self._stadium(
                qid_of(self._value(row, "venue")),
                name,
                self._value(row, "countryLabel"),
            )
            venues[qid_of(self._value(row, "club"))].append(
                Interval(
                    stadium,
                    parse_date(self._value(row, "start")),
                    parse_date(self._value(row, "end")),
                )
            )
        self.stdout.write(f"  {sum(len(v) for v in venues.values())} venue spells")
        return venues

    def _fetch_coaches(self, client, teams):
        """Group the result rows into one Coach per person and one Interval per spell.

        SPARQL returns the cross product, so a manager with dual citizenship
        yields each spell twice. Collect the attributes across every row before
        creating the Coach — taking the first row's would drop a nationality or
        date of birth that only the second carries.
        """
        rows = client.query(COACH_QUERY % self._values(teams))
        attrs, spells = {}, {}
        for row in rows:
            name = clean_name(self._value(row, "coachLabel"))
            qid = qid_of(self._value(row, "coach"))
            if not name or name == qid:  # unlabelled item
                continue
            attr = attrs.setdefault(qid, {"name": name, "nationalities": set(), "dob": ""})
            nationality = self._value(row, "nationalityLabel")
            if nationality:
                attr["nationalities"].add(nationality)
            attr["dob"] = attr["dob"] or self._value(row, "dob")
            key = (
                qid_of(self._value(row, "club")),
                qid,
                self._value(row, "start"),
                self._value(row, "end"),
            )
            spells.setdefault(key, None)

        coaches = {
            qid: self._coach(qid, a["name"], sorted(a["nationalities"]), a["dob"])
            for qid, a in attrs.items()
        }
        reigns = defaultdict(list)
        for club_qid, coach_qid, start, end in spells:
            reigns[club_qid].append(
                Interval(coaches[coach_qid], parse_date(start), parse_date(end))
            )
        self.stdout.write(f"  {sum(len(v) for v in reigns.values())} managerial spells")
        return reigns

    @staticmethod
    def _value(row, key):
        return (row.get(key) or {}).get("value", "")

    def _stadium(self, qid, name, country):
        if self.dry_run:
            return Stadium(external_id=f"wd-{qid}", name=name, country=country or "")
        stadium, _ = Stadium.objects.update_or_create(
            external_id=f"wd-{qid}", defaults={"name": name, "country": country or ""}
        )
        return stadium

    def _coach(self, qid, name, nationalities, dob):
        # Dual nationals have several citizenships and the model holds one.
        # Take the first alphabetically so re-runs don't flip it about.
        nationality = nationalities[0] if nationalities else ""
        parsed_dob = parse_date(dob)
        if self.dry_run:
            return Coach(external_id=f"wd-{qid}", name=name, nationality=nationality)
        coach, _ = Coach.objects.update_or_create(
            external_id=f"wd-{qid}",
            defaults={
                "name": name,
                "nationality": nationality,
                "date_of_birth": parsed_dob.date() if parsed_dob else None,
            },
        )
        return coach

    # -------------------------------------------------------------- backfill

    def _backfill(self, league, teams, venues, coaches):
        by_team_id = {team.id: qid for qid, team in teams.items()}
        counts = defaultdict(int)

        matches = Match.objects.filter(league=league).select_related(
            "home_team", "away_team"
        )
        for match in matches.iterator(chunk_size=500):
            fields = []
            home_qid = by_team_id.get(match.home_team_id)
            away_qid = by_team_id.get(match.away_team_id)

            if home_qid and (self.refresh or match.stadium_id is None):
                stadium, ambiguous = pick(venues.get(home_qid, []), match.kickoff)
                counts["venue_ambiguous"] += ambiguous
                if stadium is not None:
                    match.stadium = stadium
                    fields.append("stadium")
                    counts["stadium"] += 1

            for side, qid in (("home", home_qid), ("away", away_qid)):
                field = f"{side}_coach"
                if not qid or (not self.refresh and getattr(match, f"{field}_id")):
                    continue
                coach, ambiguous = pick(coaches.get(qid, []), match.kickoff)
                counts["coach_ambiguous"] += ambiguous
                if coach is not None:
                    setattr(match, field, coach)
                    fields.append(field)
                    counts["coach"] += 1

            if fields and not self.dry_run:
                match.save(update_fields=fields + ["updated_at"])
            counts["matches"] += 1

        verb = "Would set" if self.dry_run else "Set"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {counts['stadium']} stadiums and {counts['coach']} coaches "
                f"across {counts['matches']} matches "
                f"({counts['venue_ambiguous']} venue / {counts['coach_ambiguous']} "
                f"manager overlaps resolved to the narrower spell)."
            )
        )
