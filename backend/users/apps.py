from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    verbose_name = "Users"

    def ready(self):
        # Connects the "new user gets a Profile + Free subscription" receiver
        # and the login/logout/failed/locked-out -> SecurityEvent receivers.
        from . import signals  # noqa: F401
