"""Train an outcome-prediction model.

    python manage.py train_model --version v1   # logistic regression (Phase 1)
    python manage.py train_model --version v2   # XGBoost (Phase 2)
"""
from django.core.management.base import BaseCommand, CommandError

from ml.train import MODELS, train


class Command(BaseCommand):
    help = "Train a prediction model and serialize it to ml/models/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--version",
            default="v2",
            choices=list(MODELS),
            help="Model version to train (default: v2 / XGBoost).",
        )

    def handle(self, *args, **options):
        version = options["version"]
        try:
            path = train(version)
        except RuntimeError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"Model saved: {path}"))
