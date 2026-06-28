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
    # Match metadata (populated where the source provides it, e.g. StatsBomb)
    referee = models.CharField(max_length=120, blank=True)
    stadium = models.CharField(max_length=160, blank=True)
    home_manager = models.CharField(max_length=120, blank=True)
    away_manager = models.CharField(max_length=120, blank=True)

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
    # The long tail of derivable stats (passes, pass accuracy, crosses,
    # throw-ins, offsides, tackles, interceptions, saves, …) keyed
    # {"home": {...}, "away": {...}} so no source metric is dropped.
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "Match stats"

    def __str__(self):
        return f"Stats: {self.match}"


class MatchOdds(BaseModel):
    """Pre-match bookmaker odds (decimal). Sourced from football-data.co.uk CSVs,
    which already ship in each match's raw_data. Market-implied probabilities are
    derived (de-vigged) on the fly."""

    match = models.OneToOneField(
        Match, related_name="odds", on_delete=models.CASCADE
    )
    home_odds = models.FloatField(null=True, blank=True)
    draw_odds = models.FloatField(null=True, blank=True)
    away_odds = models.FloatField(null=True, blank=True)
    over25_odds = models.FloatField(null=True, blank=True)
    under25_odds = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=40, default="football-data.co.uk")

    class Meta:
        verbose_name_plural = "Match odds"

    def __str__(self):
        return f"Odds: {self.match}"

    @property
    def implied_probabilities(self):
        """De-vigged home/draw/away probabilities from the 1X2 odds, or None."""
        if not (self.home_odds and self.draw_odds and self.away_odds):
            return None
        raw = [1 / self.home_odds, 1 / self.draw_odds, 1 / self.away_odds]
        total = sum(raw)
        return {
            "home": round(raw[0] / total, 4),
            "draw": round(raw[1] / total, 4),
            "away": round(raw[2] / total, 4),
        }


class EventType(models.TextChoices):
    GOAL = "GOAL", "Goal"
    OWN_GOAL = "OWN_GOAL", "Own goal"
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
    # Goals: the assisting player. Substitutions: the player coming on (the
    # `player` field holds the player going off).
    assist = models.ForeignKey(
        Player,
        related_name="assist_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["match", "minute"]

    def __str__(self):
        return f"{self.minute}' {self.type} — {self.match}"


class MatchLineup(BaseModel):
    """A player's involvement in a single match (starting XI or bench)."""

    match = models.ForeignKey(
        Match, related_name="lineups", on_delete=models.CASCADE
    )
    team = models.ForeignKey(
        Team, related_name="lineups", on_delete=models.CASCADE
    )
    player = models.ForeignKey(
        Player, related_name="lineups", on_delete=models.CASCADE
    )
    shirt_number = models.PositiveIntegerField(null=True, blank=True)
    position = models.CharField(max_length=60, blank=True)
    is_starter = models.BooleanField(default=False)
    subbed_on_minute = models.PositiveIntegerField(null=True, blank=True)
    subbed_off_minute = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-is_starter", "shirt_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["match", "player"], name="uniq_match_player_lineup"
            )
        ]

    def __str__(self):
        return f"{self.player} ({self.match})"
