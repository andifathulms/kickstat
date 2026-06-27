"""Train outcome-prediction models.

Run inside the Django environment, e.g.:

    python manage.py train_model --version v1   # logistic regression (Phase 1)
    python manage.py train_model --version v2   # XGBoost (Phase 2)

Both build features from all FINISHED matches and serialize a model bundle to
ml/models/<version>.pkl. The bundle records its ``feature_set`` so inference
knows which feature builder to use.
"""
import joblib
from django.conf import settings
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from apps.matches.models import Match, MatchStatus

from .features import FEATURE_SETS, features_to_vector, label_for

# version name -> (feature_set key, model file stem)
MODELS = {
    "v1": ("v1", "v1_logistic"),
    "v2": ("v2", "v2_xgboost"),
}


def _model_path(stem):
    return settings.ML_MODELS_DIR / f"{stem}.pkl"


def build_dataset(feature_set):
    builder, order = FEATURE_SETS[feature_set]
    X, y = [], []
    finished = (
        Match.objects.filter(status=MatchStatus.FINISHED)
        .exclude(home_score=None)
        .exclude(away_score=None)
        .order_by("kickoff")
    )
    for match in finished:
        try:
            features = builder(match.id)
        except Exception:  # noqa: BLE001 — skip matches with incomplete history
            continue
        X.append(features_to_vector(features, order))
        y.append(label_for(match))
    return X, y


def _dump(bundle, stem):
    settings.ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = _model_path(stem)
    joblib.dump(bundle, path)
    return path


def train(version="v1"):
    """Train the requested model version. Returns the saved model path."""
    if version not in MODELS:
        raise ValueError(f"Unknown version {version}. Choose from {list(MODELS)}.")
    feature_set, stem = MODELS[version]
    X, y = build_dataset(feature_set)
    if len(set(y)) < 2 or len(X) < 20:
        raise RuntimeError(
            f"Not enough data to train (samples={len(X)}, classes={set(y)}). "
            "Run more syncs / historical ingestion first."
        )

    if version == "v1":
        path = _train_logistic(X, y, stem, feature_set)
    else:
        path = _train_xgboost(X, y, stem, feature_set)
    return path


def _train_logistic(X, y, stem, feature_set):
    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            # Multinomial is the default for LogisticRegression in sklearn 1.5+.
            ("clf", LogisticRegression(max_iter=1000, C=1.0)),
        ]
    )
    pipeline.fit(X, y)
    bundle = {
        "pipeline": pipeline,
        "feature_set": feature_set,
        "classes": list(pipeline.named_steps["clf"].classes_),
        "version": stem,
    }
    path = _dump(bundle, stem)
    print(
        f"Trained {stem} on {len(X)} matches. "
        f"Train accuracy={pipeline.score(X, y):.3f}"
    )
    print(f"Saved to {path}")
    return path


def _train_xgboost(X, y, stem, feature_set):
    from sklearn.preprocessing import LabelEncoder
    from xgboost import XGBClassifier

    encoder = LabelEncoder()
    y_enc = encoder.fit_transform(y)  # HOME/DRAW/AWAY -> 0..2 (sorted)
    clf = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="multi:softprob",
        num_class=len(encoder.classes_),
        eval_metric="mlogloss",
        tree_method="hist",
    )
    clf.fit(X, y_enc)
    # predict_proba columns are ordered 0..n; map to encoder.classes_.
    bundle = {
        "pipeline": clf,
        "feature_set": feature_set,
        "classes": list(encoder.classes_),
        "version": stem,
    }
    path = _dump(bundle, stem)
    acc = accuracy_score(y_enc, clf.predict(X))
    print(f"Trained {stem} on {len(X)} matches. Train accuracy={acc:.3f}")
    print(f"Saved to {path}")
    return path
