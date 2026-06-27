from rest_framework import serializers

from apps.leagues.serializers import LeagueSerializer, TeamMiniSerializer

from .models import Match, MatchEvent, MatchOdds, MatchStats


class MatchStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchStats
        exclude = ("match", "created_at", "updated_at")


class MatchOddsSerializer(serializers.ModelSerializer):
    implied_probabilities = serializers.SerializerMethodField()

    class Meta:
        model = MatchOdds
        fields = (
            "home_odds",
            "draw_odds",
            "away_odds",
            "over25_odds",
            "under25_odds",
            "source",
            "implied_probabilities",
        )

    def get_implied_probabilities(self, obj):
        return obj.implied_probabilities


class MatchEventSerializer(serializers.ModelSerializer):
    team = TeamMiniSerializer(read_only=True)
    player_name = serializers.CharField(source="player.name", read_only=True)

    class Meta:
        model = MatchEvent
        fields = ("id", "minute", "type", "team", "player_name", "detail")


class MatchListSerializer(serializers.ModelSerializer):
    """Compact match payload for fixture/result lists."""

    home_team = TeamMiniSerializer(read_only=True)
    away_team = TeamMiniSerializer(read_only=True)
    league_name = serializers.CharField(source="league.name", read_only=True)
    league_slug = serializers.CharField(source="league.slug", read_only=True)

    class Meta:
        model = Match
        fields = (
            "id",
            "league",
            "league_name",
            "league_slug",
            "matchday",
            "kickoff",
            "status",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
        )


class MatchListWithStatsSerializer(MatchListSerializer):
    """Compact match payload plus nested stats + odds — for the history/archive list."""

    stats = MatchStatsSerializer(read_only=True)
    odds = MatchOddsSerializer(read_only=True)

    class Meta(MatchListSerializer.Meta):
        fields = MatchListSerializer.Meta.fields + ("stats", "odds")


class MatchDetailSerializer(MatchListSerializer):
    """Full match payload: nested league, stats, events, odds, prediction."""

    league = LeagueSerializer(read_only=True)
    stats = MatchStatsSerializer(read_only=True)
    odds = MatchOddsSerializer(read_only=True)
    events = MatchEventSerializer(many=True, read_only=True)
    prediction = serializers.SerializerMethodField()

    class Meta(MatchListSerializer.Meta):
        fields = (
            "id",
            "league",
            "league_name",
            "league_slug",
            "matchday",
            "kickoff",
            "status",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            "stats",
            "odds",
            "events",
            "prediction",
        )

    def get_prediction(self, obj):
        # Imported here to avoid a circular import with the predictions app.
        from apps.predictions.serializers import MatchPredictionSerializer

        prediction = getattr(obj, "prediction", None)
        if prediction is None:
            return None
        return MatchPredictionSerializer(prediction).data
