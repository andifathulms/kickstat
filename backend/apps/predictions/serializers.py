from rest_framework import serializers

from .models import MatchPrediction


class MatchPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchPrediction
        fields = (
            "id",
            "match",
            "home_win_prob",
            "draw_prob",
            "away_win_prob",
            "predicted_outcome",
            "model_version",
            "confidence_score",
            "was_correct",
            "created_at",
        )


class PredictionCardSerializer(MatchPredictionSerializer):
    """Prediction enriched with minimal match context for the predictions hub."""

    match = serializers.SerializerMethodField()

    class Meta(MatchPredictionSerializer.Meta):
        fields = MatchPredictionSerializer.Meta.fields

    def get_match(self, obj):
        from apps.matches.serializers import MatchListSerializer

        return MatchListSerializer(obj.match).data
