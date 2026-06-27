from django.db import models
from django.utils.text import slugify

from apps.common.models import BaseModel


class Source(models.TextChoices):
    FOOTBALL_DATA = "football-data", "football-data.org"
    API_FOOTBALL = "api-football", "API-Football"


class League(BaseModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    country = models.CharField(max_length=80)
    source = models.CharField(max_length=20, choices=Source.choices)
    external_id = models.CharField(max_length=64, db_index=True)
    season = models.CharField(max_length=16, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"], name="uniq_league_source_external"
            )
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Team(BaseModel):
    name = models.CharField(max_length=120)
    short_name = models.CharField(max_length=40, blank=True)
    league = models.ForeignKey(
        League, related_name="teams", on_delete=models.CASCADE
    )
    external_id = models.CharField(max_length=64, db_index=True)
    logo_url = models.URLField(blank=True)
    source = models.CharField(max_length=20, choices=Source.choices)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"], name="uniq_team_source_external"
            )
        ]

    def __str__(self):
        return self.name


class Player(BaseModel):
    name = models.CharField(max_length=120)
    position = models.CharField(max_length=40, blank=True)
    nationality = models.CharField(max_length=80, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    team = models.ForeignKey(
        Team, related_name="players", on_delete=models.CASCADE, null=True, blank=True
    )
    external_id = models.CharField(max_length=64, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Standing(BaseModel):
    league = models.ForeignKey(
        League, related_name="standings", on_delete=models.CASCADE
    )
    team = models.ForeignKey(
        Team, related_name="standings", on_delete=models.CASCADE
    )
    season = models.CharField(max_length=16)
    position = models.PositiveIntegerField()
    played = models.PositiveIntegerField(default=0)
    won = models.PositiveIntegerField(default=0)
    drawn = models.PositiveIntegerField(default=0)
    lost = models.PositiveIntegerField(default=0)
    goals_for = models.PositiveIntegerField(default=0)
    goals_against = models.PositiveIntegerField(default=0)
    goal_difference = models.IntegerField(default=0)
    points = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["league", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["league", "team", "season"], name="uniq_standing_league_team_season"
            )
        ]

    def __str__(self):
        return f"{self.position}. {self.team} ({self.league})"
