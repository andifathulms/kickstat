from django.db import models

from apps.common.models import BaseModel
from apps.leagues.models import League, Player, Team


class MatchStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    LIVE = "LIVE", "Live"
    FINISHED = "FINISHED", "Finished"
    POSTPONED = "POSTPONED", "Postponed"
    CANCELLED = "CANCELLED", "Cancelled"


class Match(BaseModel):
    league = models.ForeignKey(
        League, related_name="matches", on_delete=models.CASCADE
    )
    home_team = models.ForeignKey(
        Team, related_name="home_matches", on_delete=models.CASCADE
    )
    away_team = models.ForeignKey(
        Team, related_name="away_matches", on_delete=models.CASCADE
    )
    matchday = models.PositiveIntegerField(null=True, blank=True)
    kickoff = models.DateTimeField()  # UTC; display conversion on frontend
    status = models.CharField(
        max_length=12, choices=MatchStatus.choices, default=MatchStatus.SCHEDULED
    )
    home_score = models.PositiveIntegerField(null=True, blank=True)
    away_score = models.PositiveIntegerField(null=True, blank=True)
    external_id = models.CharField(max_length=64, unique=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["kickoff"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["kickoff"]),
        ]

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} ({self.kickoff:%Y-%m-%d})"


class MatchStats(BaseModel):
    match = models.OneToOneField(
        Match, related_name="stats", on_delete=models.CASCADE
    )
    home_possession = models.FloatField(null=True, blank=True)
    away_possession = models.FloatField(null=True, blank=True)
    home_shots = models.PositiveIntegerField(null=True, blank=True)
    away_shots = models.PositiveIntegerField(null=True, blank=True)
    home_shots_on_target = models.PositiveIntegerField(null=True, blank=True)
    away_shots_on_target = models.PositiveIntegerField(null=True, blank=True)
    home_corners = models.PositiveIntegerField(null=True, blank=True)
    away_corners = models.PositiveIntegerField(null=True, blank=True)
    home_fouls = models.PositiveIntegerField(null=True, blank=True)
    away_fouls = models.PositiveIntegerField(null=True, blank=True)
    home_yellow_cards = models.PositiveIntegerField(null=True, blank=True)
    away_yellow_cards = models.PositiveIntegerField(null=True, blank=True)
    home_red_cards = models.PositiveIntegerField(null=True, blank=True)
    away_red_cards = models.PositiveIntegerField(null=True, blank=True)
    home_xg = models.FloatField(null=True, blank=True)
    away_xg = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Match stats"

    def __str__(self):
        return f"Stats: {self.match}"


class EventType(models.TextChoices):
    GOAL = "GOAL", "Goal"
    YELLOW = "YELLOW", "Yellow card"
    RED = "RED", "Red card"
    SUBSTITUTION = "SUBSTITUTION", "Substitution"
    VAR = "VAR", "VAR"


class MatchEvent(BaseModel):
    match = models.ForeignKey(
        Match, related_name="events", on_delete=models.CASCADE
    )
    minute = models.PositiveIntegerField(null=True, blank=True)
    type = models.CharField(max_length=16, choices=EventType.choices)
    team = models.ForeignKey(
        Team, related_name="events", on_delete=models.CASCADE, null=True, blank=True
    )
    player = models.ForeignKey(
        Player, related_name="events", on_delete=models.SET_NULL, null=True, blank=True
    )
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["match", "minute"]

    def __str__(self):
        return f"{self.minute}' {self.type} — {self.match}"
