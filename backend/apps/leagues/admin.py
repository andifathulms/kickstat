from django.contrib import admin

from .models import League, Player, Standing, Team


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "source", "season", "is_active")
    list_filter = ("source", "country", "is_active", "season")
    search_fields = ("name", "country", "external_id")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "league", "source")
    list_filter = ("source", "league")
    search_fields = ("name", "short_name", "external_id")
    autocomplete_fields = ("league",)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "nationality", "team")
    list_filter = ("position", "nationality")
    search_fields = ("name", "external_id")
    autocomplete_fields = ("team",)


@admin.register(Standing)
class StandingAdmin(admin.ModelAdmin):
    list_display = (
        "league",
        "position",
        "team",
        "played",
        "won",
        "drawn",
        "lost",
        "points",
    )
    list_filter = ("league", "season")
    search_fields = ("team__name",)
    autocomplete_fields = ("league", "team")
    ordering = ("league", "position")
