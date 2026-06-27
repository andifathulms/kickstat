"""Lightweight object factories shared across the test suite."""
from datetime import timedelta

from django.utils import timezone

from apps.leagues.models import League, Source, Standing, Team
from apps.matches.models import Match, MatchStats, MatchStatus


def make_league(**kw):
    defaults = dict(
        name="Premier League",
        country="England",
        source=Source.FOOTBALL_DATA,
        external_id="PL",
        season="2025",
    )
    defaults.update(kw)
    return League.objects.create(**defaults)


def make_team(league, name="Arsenal", external_id="57", **kw):
    return Team.objects.create(
        name=name,
        short_name=name[:3].upper(),
        league=league,
        external_id=external_id,
        source=league.source,
        **kw,
    )


def make_match(league, home, away, **kw):
    defaults = dict(
        league=league,
        home_team=home,
        away_team=away,
        matchday=1,
        kickoff=timezone.now() + timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
        external_id="m-1",
    )
    defaults.update(kw)
    return Match.objects.create(**defaults)


def make_standing(league, team, position=1, **kw):
    defaults = dict(
        league=league,
        team=team,
        season=league.season,
        position=position,
        played=10,
        won=7,
        drawn=2,
        lost=1,
        goals_for=20,
        goals_against=8,
        goal_difference=12,
        points=23,
    )
    defaults.update(kw)
    return Standing.objects.create(**defaults)


def make_stats(match, **kw):
    return MatchStats.objects.create(match=match, **kw)
