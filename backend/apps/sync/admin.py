from django.contrib import admin

from .models import SyncLog


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "task",
        "target",
        "records_created",
        "records_updated",
        "duration_ms",
        "success",
    )
    list_filter = ("task", "success")
    search_fields = ("task", "target", "errors")
    readonly_fields = (
        "task",
        "target",
        "records_created",
        "records_updated",
        "errors",
        "duration_ms",
        "success",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"
