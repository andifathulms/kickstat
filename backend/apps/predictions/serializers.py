from rest_framework import serializers

from .models import MatchPrediction, MatchScorePrediction


class MatchScorePredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchScorePrediction
        fields = (
            "lambda_home",
            "lambda_away",
            "most_likely_home",
            "most_likely_away",
            "most_likely_prob",
            "home_win_prob",
            "draw_prob",
            "away_win_prob",
            "over25_prob",
            "btts_prob",
            "top_scores",
            "model_version",
        )


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
