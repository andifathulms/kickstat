from django.db import models

from apps.common.models import BaseModel


class SyncLog(BaseModel):
    """One row per sync task run, for monitoring sync health in the admin."""

    task = models.CharField(max_length=120)
    target = models.CharField(max_length=120, blank=True)  # e.g. league name/id
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    errors = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    success = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        status = "ok" if self.success else "FAIL"
        return f"[{status}] {self.task} {self.target} (+{self.records_created}/~{self.records_updated})"
