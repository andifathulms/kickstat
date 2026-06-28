from django.contrib import admin, messages

from ml.evaluate import accuracy_report, evaluate_unscored

from .models import MatchPrediction, MatchScorePrediction


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
    change_list_template = "admin/predictions/matchprediction/change_list.html"
    actions = ["run_evaluation"]

    def changelist_view(self, request, extra_context=None):
        """Inject the per-model accuracy summary above the prediction list."""
        extra_context = extra_context or {}
        extra_context["accuracy_report"] = accuracy_report()
        return super().changelist_view(request, extra_context=extra_context)

    @admin.action(description="Evaluate finished predictions (fill accuracy)")
    def run_evaluation(self, request, queryset):
        scored, correct = evaluate_unscored()
        self.message_user(
            request,
            f"Evaluated {scored} finished prediction(s); {correct} correct.",
            level=messages.SUCCESS,
        )


@admin.register(MatchScorePrediction)
class MatchScorePredictionAdmin(admin.ModelAdmin):
    list_display = (
        "match",
        "most_likely_home",
        "most_likely_away",
        "lambda_home",
        "lambda_away",
        "over25_prob",
        "btts_prob",
        "model_version",
    )
    list_filter = ("model_version",)
    search_fields = ("match__home_team__name", "match__away_team__name")
    autocomplete_fields = ("match",)
