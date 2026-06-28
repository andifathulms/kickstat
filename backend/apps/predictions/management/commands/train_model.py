"""Train an outcome-prediction model.

    python manage.py train_model --variant v1   # logistic regression (Phase 1)
    python manage.py train_model --variant v2   # XGBoost (Phase 2)
"""
from django.core.management.base import BaseCommand, CommandError

from ml.train import MODELS, train


class Command(BaseCommand):
    help = "Train a prediction model and serialize it to ml/models/."

    def add_arguments(self, parser):
        # NB: --version is reserved by Django's base command, so use --variant.
        parser.add_argument(
            "--variant",
            default="v3",
            choices=list(MODELS),
            help="Model variant to train (default: v3 / XGBoost with odds + rich stats).",
        )

    def handle(self, *args, **options):
        variant = options["variant"]
        try:
            path = train(variant)
        except RuntimeError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"Model saved: {path}"))
