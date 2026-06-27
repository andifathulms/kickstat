"""Train the Phase 1 logistic regression outcome model.

Run inside the Django environment, e.g.:

    python manage.py shell -c "from ml.train import train; train()"

Builds features from all FINISHED matches, fits a multinomial logistic regression
over [HOME, DRAW, AWAY], and serializes the pipeline to ml/models/v1_logistic.pkl.
"""
import joblib
from django.conf import settings
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from apps.matches.models import Match, MatchStatus

from .features import FEATURE_ORDER, features_to_vector, get_features, label_for

MODEL_VERSION = "v1_logistic"
MODEL_PATH = settings.ML_MODELS_DIR / f"{MODEL_VERSION}.pkl"


def build_dataset():
    X, y = [], []
    finished = (
        Match.objects.filter(status=MatchStatus.FINISHED)
        .exclude(home_score=None)
        .exclude(away_score=None)
        .order_by("kickoff")
    )
    for match in finished:
        try:
            features = get_features(match.id)
        except Exception:  # noqa: BLE001 — skip matches with incomplete history
            continue
        X.append(features_to_vector(features))
        y.append(label_for(match))
    return X, y


def train():
    X, y = build_dataset()
    if len(set(y)) < 2 or len(X) < 20:
        raise RuntimeError(
            f"Not enough data to train (samples={len(X)}, classes={set(y)}). "
            "Run more syncs / StatsBomb ingestion first."
        )

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            # Multinomial is the default for LogisticRegression in sklearn 1.5+.
            ("clf", LogisticRegression(max_iter=1000, C=1.0)),
        ]
    )
    pipeline.fit(X, y)

    settings.ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": pipeline,
            "feature_order": FEATURE_ORDER,
            "classes": list(pipeline.named_steps["clf"].classes_),
            "version": MODEL_VERSION,
        },
        MODEL_PATH,
    )
    accuracy = pipeline.score(X, y)
    print(f"Trained {MODEL_VERSION} on {len(X)} matches. Train accuracy={accuracy:.3f}")
    print(f"Saved to {MODEL_PATH}")
    return MODEL_PATH


if __name__ == "__main__":
    import django

    django.setup()
    train()
