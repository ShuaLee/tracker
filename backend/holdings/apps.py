from django.apps import AppConfig


class HoldingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "holdings"

    def ready(self):
        # Connects the "new user gets a default portfolio" receiver. It lives
        # here, not in accounts, because accounts may import nothing else in
        # the project (PLAN.md 1.1).
        from . import signals  # noqa: F401
