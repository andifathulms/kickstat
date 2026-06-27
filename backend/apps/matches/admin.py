from django.contrib import admin

from .models import Match, MatchEvent, MatchOdds, MatchStats


class MatchStatsInline(admin.StackedInline):
    model = MatchStats
    extra = 0


class MatchEventInline(admin.TabularInline):
    model = MatchEvent
    extra = 0
    autocomplete_fields = ("team", "player")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "kickoff",
        "home_team",
        "home_score",
        "away_score",
        "away_team",
        "status",
        "league",
    )
    list_filter = ("status", "league", "matchday")
    search_fields = ("home_team__name", "away_team__name", "external_id")
    autocomplete_fields = ("league", "home_team", "away_team")
    date_hierarchy = "kickoff"
    inlines = (MatchStatsInline, MatchEventInline)


@admin.register(MatchStats)
class MatchStatsAdmin(admin.ModelAdmin):
    list_display = ("match", "home_possession", "away_possession", "home_xg", "away_xg")
    search_fields = ("match__home_team__name", "match__away_team__name")
    autocomplete_fields = ("match",)


@admin.register(MatchOdds)
class MatchOddsAdmin(admin.ModelAdmin):
    list_display = ("match", "home_odds", "draw_odds", "away_odds", "source")
    search_fields = ("match__home_team__name", "match__away_team__name")
    autocomplete_fields = ("match",)


@admin.register(MatchEvent)
class MatchEventAdmin(admin.ModelAdmin):
    list_display = ("match", "minute", "type", "team", "player")
    list_filter = ("type",)
    search_fields = ("match__home_team__name", "match__away_team__name", "player__name")
    autocomplete_fields = ("match", "team", "player")
