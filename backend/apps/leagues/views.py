from django.db.models import Count, Max, Min, Q
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
    def standings(self, request, pk=None):
        league = self.get_object()
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
