from django.contrib import admin

from .models import MatchPrediction


@admin.register(MatchPrediction)
class MatchPredictionAdmin(admin.ModelAdmin):
    list_display = (
        "match",
        "predicted_outcome",
        "home_win_prob",
        "draw_prob",
        "away_win_prob",
        "confidence_score",
        "model_version",
        "was_correct",
    )
    list_filter = ("predicted_outcome", "model_version", "was_correct")
    search_fields = ("match__home_team__name", "match__away_team__name")
    autocomplete_fields = ("match",)
