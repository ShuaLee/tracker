from django.apps import AppConfig


class PortfoliosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "portfolios"
    verbose_name = "Portfolios"

    def ready(self):
        # Connects "new user gets a portfolio" and "portfolio follows the
        # profile's base currency". They live here, not in users, because
        # users may not import any other project app (PLAN.md 3).
        from . import signals  # noqa: F401
