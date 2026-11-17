from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        # Connects the post_save-creates-Profile receiver and the
        # login/logout/login_failed/locked-out -> SecurityEvent receivers.
        from . import signals  # noqa: F401
