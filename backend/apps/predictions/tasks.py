"""Celery tasks for running and evaluating match predictions.

- run_daily_predictions: 08:00 WIB — predict today's SCHEDULED/LIVE fixtures
- evaluate_predictions:   00:00 WIB — score yesterday's predictions
"""
import logging

from celery import shared_task
from django.utils import timezone

from apps.matches.models import Match, MatchStatus

from .models import MatchPrediction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_daily_predictions(self):
    """Generate predictions for today's upcoming fixtures."""
    # Imported lazily so the worker only loads sklearn/joblib when needed.
    from ml.predict import predict_match

    today = timezone.now().date()
    fixtures = Match.objects.filter(
        kickoff__date=today,
        status__in=[MatchStatus.SCHEDULED, MatchStatus.LIVE],
    )

    created = updated = skipped = 0
    for match in fixtures:
        try:
            result = predict_match(match.id)
        except FileNotFoundError:
            logger.warning("No trained model found; skipping predictions.")
            return {"error": "model_not_found"}
        except Exception as exc:  # noqa: BLE001 — one bad match shouldn't abort the run
            logger.warning("Prediction failed for match %s: %s", match.id, exc)
            skipped += 1
            continue

        _, was_created = MatchPrediction.objects.update_or_create(
            match=match, defaults=result
        )
        created += int(was_created)
        updated += int(not was_created)

    logger.info(
        "run_daily_predictions: created=%s updated=%s skipped=%s",
        created,
        updated,
        skipped,
    )
    return {"created": created, "updated": updated, "skipped": skipped}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def evaluate_predictions(self):
    """Score finished matches' predictions (fills was_correct)."""
    from ml.evaluate import accuracy_by_version, evaluate_unscored

    scored, correct = evaluate_unscored()
    logger.info(
        "evaluate_predictions: scored=%s correct=%s accuracy_by_version=%s",
        scored,
        correct,
        accuracy_by_version(),
    )
    return {"scored": scored, "correct": correct}
