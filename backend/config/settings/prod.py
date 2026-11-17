"""
Production. Not the default - a real deployment must set

    DJANGO_SETTINGS_MODULE=config.settings.prod

explicitly. `manage.py check --deploy --settings=config.settings.prod` should
run clean against this module (with a fully-populated environment).
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# A real email provider, not the console backend. SMTP is the lowest common
# denominator every provider supports; swap EMAIL_BACKEND for a
# provider-specific one later without touching accounts/emails.py.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
