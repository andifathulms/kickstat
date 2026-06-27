"""Score predictions against actual results via the ``was_correct`` field."""
from apps.matches.models import MatchStatus
from apps.predictions.models import MatchPrediction, Outcome


def _actual_outcome(match):
    if match.home_score is None or match.away_score is None:
        return None
    if match.home_score > match.away_score:
        return Outcome.HOME
    if match.home_score == match.away_score:
        return Outcome.DRAW
    return Outcome.AWAY


def evaluate_unscored():
    """Fill ``was_correct`` for predictions whose match is now finished.

    Returns (scored_count, correct_count).
    """
    pending = MatchPrediction.objects.filter(
        was_correct__isnull=True, match__status=MatchStatus.FINISHED
    ).select_related("match")

    scored = correct = 0
    for prediction in pending:
        actual = _actual_outcome(prediction.match)
        if actual is None:
            continue
        prediction.was_correct = prediction.predicted_outcome == actual
        prediction.save(update_fields=["was_correct", "updated_at"])
        scored += 1
        correct += int(prediction.was_correct)
    return scored, correct


def accuracy_by_version():
    """Return {model_version: accuracy} over all scored predictions."""
    result = {}
    versions = (
        MatchPrediction.objects.exclude(was_correct__isnull=True)
        .values_list("model_version", flat=True)
        .distinct()
    )
    for version in versions:
        qs = MatchPrediction.objects.filter(
            model_version=version, was_correct__isnull=False
        )
        total = qs.count()
        hits = qs.filter(was_correct=True).count()
        result[version] = round(hits / total, 4) if total else 0.0
    return result


def accuracy_report():
    """Per-version breakdown for the admin dashboard.

    Returns a list of dicts ordered by accuracy desc:
    {version, total, scored, correct, pending, accuracy_pct}
    where ``pending`` counts predictions still awaiting a result.
    """
    rows = []
    versions = (
        MatchPrediction.objects.values_list("model_version", flat=True)
        .distinct()
        .order_by("model_version")
    )
    for version in versions:
        qs = MatchPrediction.objects.filter(model_version=version)
        total = qs.count()
        scored = qs.filter(was_correct__isnull=False).count()
        correct = qs.filter(was_correct=True).count()
        rows.append(
            {
                "version": version,
                "total": total,
                "scored": scored,
                "correct": correct,
                "pending": total - scored,
                "accuracy_pct": round(100 * correct / scored, 1) if scored else None,
            }
        )
    rows.sort(key=lambda r: (r["accuracy_pct"] is not None, r["accuracy_pct"] or 0), reverse=True)
    return rows
