import datetime

from django.db.models import Count, Max, Min, Q
from django.db.models.functions import ExtractMonth, ExtractYear
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.matches.models import Match, MatchStatus
from apps.matches.serializers import MatchListSerializer

from .models import League, Standing, Team
from .serializers import (
    LeagueSerializer,
    StandingSerializer,
    TeamSerializer,
)


# Season boundary: a football season starting in `year` runs Aug–Jul. August
# (not July) so the COVID-extended 2019/20 season — which finished in July
# 2020 — stays in 2019/20 rather than leaking into 2020/21. Suits the Aug–May
# European leagues we hold history for.
SEASON_CUTOFF_MONTH = 8


def season_of(year: int, month: int) -> int:
    return year if month >= SEASON_CUTOFF_MONTH else year - 1


def _season_bounds(year: int) -> tuple[datetime.date, datetime.date]:
    """UTC date window for a football season starting in `year` (Aug–Jul)."""
    return datetime.date(year, 8, 1), datetime.date(year + 1, 7, 31)


def _compute_standings(
    league: League, season: str, date_from, date_to, venue: str = "overall"
) -> list[dict]:
    """Derive a league table from finished matches in a date window.

    venue: "overall" (default), "home" (each team's home matches only) or
    "away" (away matches only).
    """
    matches = Match.objects.filter(
        league=league,
        status=MatchStatus.FINISHED,
        kickoff__date__gte=date_from,
        kickoff__date__lte=date_to,
        home_score__isnull=False,
        away_score__isnull=False,
    ).select_related("home_team", "away_team")

    table: dict[int, dict] = {}

    def row(team):
        if team.id not in table:
            table[team.id] = {
                "team": team,
                "played": 0,
                "won": 0,
                "drawn": 0,
                "lost": 0,
                "goals_for": 0,
                "goals_against": 0,
                "points": 0,
            }
        return table[team.id]

    def credit(team, gf, ga):
        r = row(team)
        r["played"] += 1
        r["goals_for"] += gf
        r["goals_against"] += ga
        if gf > ga:
            r["won"] += 1
            r["points"] += 3
        elif gf < ga:
            r["lost"] += 1
        else:
            r["drawn"] += 1
            r["points"] += 1

    for m in matches:
        hs, as_ = m.home_score, m.away_score
        if venue in ("overall", "home"):
            credit(m.home_team, hs, as_)
        if venue in ("overall", "away"):
            credit(m.away_team, as_, hs)

    rows = list(table.values())
    for r in rows:
        r["goal_difference"] = r["goals_for"] - r["goals_against"]
    rows.sort(
        key=lambda r: (
            -r["points"],
            -r["goal_difference"],
            -r["goals_for"],
            r["team"].name,
        )
    )

    return [
        {
            "id": r["team"].id,  # synthetic; unique within this table
            "season": season,
            "position": i,
            "team": {
                "id": r["team"].id,
                "name": r["team"].name,
                "short_name": r["team"].short_name,
                "logo_url": r["team"].logo_url,
            },
            "played": r["played"],
            "won": r["won"],
            "drawn": r["drawn"],
            "lost": r["lost"],
            "goals_for": r["goals_for"],
            "goals_against": r["goals_against"],
            "goal_difference": r["goal_difference"],
            "points": r["points"],
            "computed": True,
        }
        for i, r in enumerate(rows, start=1)
    ]


class LeagueViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = League.objects.all()
    serializer_class = LeagueSerializer
    filterset_fields = ["source", "country", "is_active"]
    lookup_value_regex = r"[^/]+"  # allow id or slug

    def get_object(self):
        value = self.kwargs["pk"]
        qs = self.get_queryset()
        if value.isdigit():
            return qs.get(pk=value)
        return qs.get(slug=value)

    @action(detail=False)
    def archive(self, request):
        """Historical (non-live) leagues with match counts and year span."""
        qs = (
            League.objects.filter(is_active=False)
            .annotate(
                match_count=Count("matches"),
                first_year=Min("matches__kickoff"),
                last_year=Max("matches__kickoff"),
            )
            .filter(match_count__gt=0)
            .order_by("-match_count")
        )
        data = [
            {
                "id": l.id,
                "name": l.name,
                "slug": l.slug,
                "country": l.country,
                "match_count": l.match_count,
                "first_year": l.first_year.year if l.first_year else None,
                "last_year": l.last_year.year if l.last_year else None,
            }
            for l in qs
        ]
        return Response(data)

    @action(detail=True)
    def seasons(self, request, pk=None):
        """Seasons that actually have matches (Jul–Jun), newest first.

        Avoids surfacing empty placeholder seasons — the table is derived from
        real fixtures, not from a possibly-stale stored standings row.
        """
        league = self.get_object()
        grouped = (
            Match.objects.filter(league=league)
            .annotate(y=ExtractYear("kickoff"), mo=ExtractMonth("kickoff"))
            .values("y", "mo")
            .annotate(c=Count("id"))
        )
        counts: dict[int, int] = {}
        for g in grouped:
            season = season_of(g["y"], g["mo"])
            counts[season] = counts.get(season, 0) + g["c"]
        data = [
            {"season": str(s), "match_count": counts[s]}
            for s in sorted(counts, reverse=True)
        ]
        return Response(data)

    @action(detail=True)
    def standings(self, request, pk=None):
        league = self.get_object()
        season = request.query_params.get("season")
        venue = request.query_params.get("venue", "overall")
        if venue not in ("overall", "home", "away"):
            venue = "overall"

        if season:
            # Home/away splits aren't carried in stored standings, so always
            # compute them. For overall, prefer real stored rows when present.
            if venue == "overall":
                stored = list(
                    Standing.objects.filter(league=league, season=season)
                    .select_related("team")
                    .order_by("position")
                )
                if stored and any(s.played > 0 for s in stored):
                    return Response(StandingSerializer(stored, many=True).data)
            try:
                year = int(season)
            except ValueError:
                return Response([])
            date_from, date_to = _season_bounds(year)
            return Response(
                _compute_standings(league, season, date_from, date_to, venue)
            )

        qs = (
            Standing.objects.filter(league=league)
            .select_related("team")
            .order_by("position")
        )
        return Response(StandingSerializer(qs, many=True).data)

    @action(detail=True)
    def fixtures(self, request, pk=None):
        league = self.get_object()
        qs = (
            Match.objects.filter(
                league=league,
                status__in=[MatchStatus.SCHEDULED, MatchStatus.LIVE],
            )
            .select_related("home_team", "away_team", "league")
            .order_by("kickoff")
        )
        page = self.paginate_queryset(qs)
        serializer = MatchListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True)
    def results(self, request, pk=None):
        league = self.get_object()
        qs = (
            Match.objects.filter(league=league, status=MatchStatus.FINISHED)
            .select_related("home_team", "away_team", "league")
            .order_by("-kickoff")
        )
        page = self.paginate_queryset(qs)
        serializer = MatchListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Team.objects.select_related("league").all()
    serializer_class = TeamSerializer
    filterset_fields = ["league", "source"]

    @action(detail=True)
    def form(self, request, pk=None):
        """Last 5 finished matches for the team (most recent first)."""
        team = self.get_object()
        qs = (
            Match.objects.filter(Q(home_team=team) | Q(away_team=team))
            .filter(status=MatchStatus.FINISHED)
            .select_related("home_team", "away_team", "league")
            .order_by("-kickoff")[:5]
        )
        return Response(MatchListSerializer(qs, many=True).data)

    @action(detail=True)
    def fixtures(self, request, pk=None):
        team = self.get_object()
        qs = (
            Match.objects.filter(Q(home_team=team) | Q(away_team=team))
            .filter(status__in=[MatchStatus.SCHEDULED, MatchStatus.LIVE])
            .select_related("home_team", "away_team", "league")
            .order_by("kickoff")
        )
        return Response(MatchListSerializer(qs, many=True).data)

    @action(detail=True)
    def stats(self, request, pk=None):
        """Aggregate season stats derived from finished matches."""
        team = self.get_object()
        finished = Match.objects.filter(status=MatchStatus.FINISHED)
        home = finished.filter(home_team=team)
        away = finished.filter(away_team=team)

        def goals(qs, field):
            return sum(getattr(m, field) or 0 for m in qs)

        played = home.count() + away.count()
        scored = goals(home, "home_score") + goals(away, "away_score")
        conceded = goals(home, "away_score") + goals(away, "home_score")
        return Response(
            {
                "team": team.id,
                "played": played,
                "goals_scored": scored,
                "goals_conceded": conceded,
                "goals_scored_avg": round(scored / played, 2) if played else 0,
                "goals_conceded_avg": round(conceded / played, 2) if played else 0,
            }
        )
