from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.matches.models import MatchStatus

from .models import MatchPrediction
from .serializers import MatchPredictionSerializer, PredictionCardSerializer


class PredictionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MatchPrediction.objects.select_related(
        "match__home_team", "match__away_team", "match__league"
    ).all()
    serializer_class = MatchPredictionSerializer
    filterset_fields = ["predicted_outcome", "model_version", "was_correct"]

    @action(detail=False)
    def today(self, request):
        """Top predictions for today's upcoming/live fixtures, by confidence."""
        today = timezone.now().date()
        qs = (
            self.get_queryset()
            .filter(
                match__kickoff__date=today,
                match__status__in=[MatchStatus.SCHEDULED, MatchStatus.LIVE],
            )
            .order_by("-confidence_score")
        )
        return Response(PredictionCardSerializer(qs, many=True).data)
