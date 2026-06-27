"""Celery application for Kickstat with the Celery Beat schedule from the PRD."""
import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("kickstat")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Schedule times are WIB (CELERY_TIMEZONE = Asia/Jakarta). See PRD "API Sync Architecture".
app.conf.beat_schedule = {
    # football-data.org — no daily cap
    "sync-standings": {
        "task": "apps.sync.tasks.football_data.sync_all_standings",
        "schedule": crontab(hour=6, minute=0),
    },
    "sync-fixtures-7days": {
        "task": "apps.sync.tasks.football_data.sync_all_fixtures",
        "schedule": crontab(hour=6, minute=30),
    },
    "sync-live-scores": {
        "task": "apps.sync.tasks.football_data.sync_live_scores",
        "schedule": crontab(minute="*/5"),
    },
    "sync-finished-matches": {
        "task": "apps.sync.tasks.football_data.sync_all_results",
        "schedule": crontab(hour=23, minute=30),
    },
    # API-Football — Liga 1 only, conserve quota
    "sync-liga1-fixtures": {
        "task": "apps.sync.tasks.api_football.sync_liga1_fixtures",
        "schedule": crontab(hour=5, minute=0, day_of_week="mon"),
    },
    "sync-liga1-results": {
        "task": "apps.sync.tasks.api_football.sync_liga1_results",
        "schedule": crontab(hour=23, minute=0),
    },
    # Predictions
    "run-predictions": {
        "task": "apps.predictions.tasks.run_daily_predictions",
        "schedule": crontab(hour=8, minute=0),
    },
    "evaluate-predictions": {
        "task": "apps.predictions.tasks.evaluate_predictions",
        "schedule": crontab(hour=0, minute=0),
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
