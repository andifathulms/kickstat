from django.db import models

from apps.common.models import BaseModel
from apps.matches.models import Match


class Outcome(models.TextChoices):
    HOME = "HOME", "Home win"
    DRAW = "DRAW", "Draw"
    AWAY = "AWAY", "Away win"


class MatchPrediction(BaseModel):
    match = models.OneToOneField(
        Match, related_name="prediction", on_delete=models.CASCADE
    )
    home_win_prob = models.FloatField()
    draw_prob = models.FloatField()
    away_win_prob = models.FloatField()
    predicted_outcome = models.CharField(max_length=8, choices=Outcome.choices)
    model_version = models.CharField(max_length=32)
    confidence_score = models.FloatField()
    was_correct = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ["-confidence_score"]
        indexes = [models.Index(fields=["model_version"])]

    def __str__(self):
        return f"Prediction {self.predicted_outcome} — {self.match}"


class MatchScorePrediction(BaseModel):
    """Poisson scoreline prediction: expected goals, most-likely score, and
    distribution-derived markets (1X2, over 2.5, both-teams-to-score)."""

    match = models.OneToOneField(
        Match, related_name="score_prediction", on_delete=models.CASCADE
    )
    lambda_home = models.FloatField()  # expected home goals
    lambda_away = models.FloatField()
    most_likely_home = models.PositiveIntegerField()
    most_likely_away = models.PositiveIntegerField()
    most_likely_prob = models.FloatField()
    home_win_prob = models.FloatField()
    draw_prob = models.FloatField()
    away_win_prob = models.FloatField()
    over25_prob = models.FloatField()
    btts_prob = models.FloatField()
    top_scores = models.JSONField(default=list, blank=True)
    model_version = models.CharField(max_length=32, default="poisson_v1")

    class Meta:
        indexes = [models.Index(fields=["model_version"])]

    def __str__(self):
        return (
            f"Scoreline {self.most_likely_home}-{self.most_likely_away} — {self.match}"
        )
