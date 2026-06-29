from rest_framework import serializers

from .models import Coach, League, Player, Standing, Team


class CoachSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coach
        fields = ("id", "name", "nationality", "date_of_birth")


class LeagueSerializer(serializers.ModelSerializer):
    class Meta:
        model = League
        fields = (
            "id",
            "name",
            "slug",
            "country",
            "source",
            "season",
            "is_active",
        )


class TeamSerializer(serializers.ModelSerializer):
    league_name = serializers.CharField(source="league.name", read_only=True)

    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "short_name",
            "logo_url",
            "league",
            "league_name",
            "source",
        )


class TeamMiniSerializer(serializers.ModelSerializer):
    """Compact team representation embedded in match/standing payloads."""

    class Meta:
        model = Team
        fields = ("id", "name", "short_name", "logo_url")


class PlayerSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = Player
        fields = (
            "id",
            "name",
            "nickname",
            "position",
            "nationality",
            "date_of_birth",
            "team",
            "team_name",
        )


class StandingSerializer(serializers.ModelSerializer):
    team = TeamMiniSerializer(read_only=True)

    class Meta:
        model = Standing
        fields = (
            "id",
            "season",
            "position",
            "team",
            "played",
            "won",
            "drawn",
            "lost",
            "goals_for",
            "goals_against",
            "goal_difference",
            "points",
        )
