from rest_framework import serializers

from apps.leagues.serializers import LeagueSerializer, TeamMiniSerializer

from .models import Match, MatchEvent, MatchLineup, MatchOdds, MatchStats


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
    team = serializers.IntegerField(source="team_id", read_only=True)
    player_name = serializers.CharField(source="player.name", read_only=True)
    assist_name = serializers.CharField(source="assist.name", read_only=True)

    class Meta:
        model = MatchEvent
        fields = (
            "id",
            "minute",
            "type",
            "team",
            "player_name",
            "assist_name",
            "detail",
        )


class MatchLineupSerializer(serializers.ModelSerializer):
    team = serializers.IntegerField(source="team_id", read_only=True)
    player_id = serializers.IntegerField(read_only=True)
    player_name = serializers.CharField(source="player.name", read_only=True)
    player_nickname = serializers.CharField(
        source="player.nickname", read_only=True
    )

    class Meta:
        model = MatchLineup
        fields = (
            "team",
            "player_id",
            "player_name",
            "player_nickname",
            "shirt_number",
            "position",
            "is_starter",
            "subbed_on_minute",
            "subbed_off_minute",
        )


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
    lineups = MatchLineupSerializer(many=True, read_only=True)
    prediction = serializers.SerializerMethodField()
    score_prediction = serializers.SerializerMethodField()

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
            "referee",
            "stadium",
            "home_manager",
            "away_manager",
            "stats",
            "odds",
            "events",
            "lineups",
            "prediction",
            "score_prediction",
        )

    def get_prediction(self, obj):
        # Imported here to avoid a circular import with the predictions app.
        from apps.predictions.serializers import MatchPredictionSerializer

        prediction = getattr(obj, "prediction", None)
        if prediction is None:
            return None
        return MatchPredictionSerializer(prediction).data

    def get_score_prediction(self, obj):
        from apps.predictions.serializers import MatchScorePredictionSerializer

        sp = getattr(obj, "score_prediction", None)
        if sp is None:
            return None
        return MatchScorePredictionSerializer(sp).data
