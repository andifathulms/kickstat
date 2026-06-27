"""Inference: load the trained model and predict a match outcome."""
import joblib
from django.conf import settings

from .features import features_to_vector, get_features

MODEL_VERSION = "v1_logistic"
MODEL_PATH = settings.ML_MODELS_DIR / f"{MODEL_VERSION}.pkl"

_OUTCOME_FROM_LABEL = {"HOME": "HOME", "DRAW": "DRAW", "AWAY": "AWAY"}

_cache = {}


def load_model(path=MODEL_PATH):
    """Load and memoize the serialized model bundle."""
    key = str(path)
    if key not in _cache:
        _cache[key] = joblib.load(path)
    return _cache[key]


def predict_match(match_id: int) -> dict:
    """Return probability dict + predicted outcome for a match.

    {
        'home_win_prob', 'draw_prob', 'away_win_prob',
        'predicted_outcome', 'confidence_score', 'model_version'
    }
    """
    bundle = load_model()
    pipeline = bundle["pipeline"]
    classes = bundle["classes"]

    features = get_features(match_id)
    vector = [features_to_vector(features)]
    probs = pipeline.predict_proba(vector)[0]
    prob_by_class = {cls: float(p) for cls, p in zip(classes, probs)}

    home = prob_by_class.get("HOME", 0.0)
    draw = prob_by_class.get("DRAW", 0.0)
    away = prob_by_class.get("AWAY", 0.0)
    predicted = max(prob_by_class, key=prob_by_class.get)

    return {
        "home_win_prob": round(home, 4),
        "draw_prob": round(draw, 4),
        "away_win_prob": round(away, 4),
        "predicted_outcome": _OUTCOME_FROM_LABEL[predicted],
        "confidence_score": round(max(home, draw, away), 4),
        "model_version": bundle["version"],
    }
