from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from .filters import MatchFilter
from .models import Match, MatchStatus
from .serializers import (
    MatchDetailSerializer,
    MatchEventSerializer,
    MatchListSerializer,
    MatchListWithStatsSerializer,
    MatchStatsSerializer,
)


class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    filterset_class = MatchFilter
    ordering_fields = ["kickoff"]
    ordering = ["kickoff"]

    def _wants_stats(self):
        return self.request.query_params.get("with_stats") in ("1", "true", "True")

    def get_queryset(self):
        qs = Match.objects.select_related(
            "league", "home_team", "away_team"
        )
        if self.action == "retrieve":
            qs = qs.select_related("stats", "odds").prefetch_related(
                "events__team", "events__player", "prediction"
            )
        elif self._wants_stats():
            qs = qs.select_related("stats", "odds")
        return qs.order_by("kickoff")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MatchDetailSerializer
        if self.action == "list" and self._wants_stats():
            return MatchListWithStatsSerializer
        return MatchListSerializer

    @action(detail=False)
    def live(self, request):
        qs = self.get_queryset().filter(status=MatchStatus.LIVE)
        return Response(MatchListSerializer(qs, many=True).data)

    @action(detail=True)
    def stats(self, request, pk=None):
        match = get_object_or_404(Match, pk=pk)
        stats = getattr(match, "stats", None)
        if stats is None:
            return Response({})
        return Response(MatchStatsSerializer(stats).data)

    @action(detail=True)
    def events(self, request, pk=None):
        match = get_object_or_404(Match, pk=pk)
        qs = match.events.select_related("team", "player").order_by("minute")
        return Response(MatchEventSerializer(qs, many=True).data)

    @action(detail=True)
    def prediction(self, request, pk=None):
        from apps.predictions.serializers import MatchPredictionSerializer

        match = get_object_or_404(Match, pk=pk)
        prediction = getattr(match, "prediction", None)
        if prediction is None:
            return Response({}, status=404)
        return Response(MatchPredictionSerializer(prediction).data)
