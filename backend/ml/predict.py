"""Inference: load the active trained model and predict a match outcome."""
import joblib
from django.conf import settings

from .features import FEATURE_SETS, features_to_vector

# Preference order when resolving which serialized model to serve.
MODEL_PREFERENCE = ["v3_xgboost", "v2_xgboost", "v1_logistic"]

_cache = {}


def _model_path(stem):
    return settings.ML_MODELS_DIR / f"{stem}.pkl"


def resolve_model_path():
    """Return the best available model file, honouring settings.ML_ACTIVE_MODEL.

    Falls back through MODEL_PREFERENCE so a missing preferred model degrades to
    an older one rather than failing. Raises FileNotFoundError if none exist.
    """
    preferred = getattr(settings, "ML_ACTIVE_MODEL", MODEL_PREFERENCE[0])
    order = [preferred] + [m for m in MODEL_PREFERENCE if m != preferred]
    for stem in order:
        path = _model_path(stem)
        if path.exists():
            return path
    raise FileNotFoundError(
        f"No trained model found in {settings.ML_MODELS_DIR}. Run train_model first."
    )


def load_model(path=None):
    """Load and memoize the serialized model bundle (active model by default)."""
    if path is None:
        path = resolve_model_path()
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
    model = bundle["pipeline"]
    classes = bundle["classes"]

    feature_set = bundle.get("feature_set", "v1")
    builder, order = FEATURE_SETS[feature_set]
    features = builder(match_id)
    vector = [features_to_vector(features, order)]
    probs = model.predict_proba(vector)[0]
    prob_by_class = {cls: float(p) for cls, p in zip(classes, probs)}

    home = prob_by_class.get("HOME", 0.0)
    draw = prob_by_class.get("DRAW", 0.0)
    away = prob_by_class.get("AWAY", 0.0)
    predicted = max(prob_by_class, key=prob_by_class.get)

    return {
        "home_win_prob": round(home, 4),
        "draw_prob": round(draw, 4),
        "away_win_prob": round(away, 4),
        "predicted_outcome": predicted,
        "confidence_score": round(max(home, draw, away), 4),
        "model_version": bundle["version"],
    }
