"""Local development. Default DJANGO_SETTINGS_MODULE (see manage.py / wsgi.py / asgi.py)."""

from .base import *  # noqa: F401,F403

DEBUG = True

# Dev normally runs over plain http://localhost - these would otherwise
# make the session/CSRF cookies silently never get sent.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Verification, password-reset and notice emails are printed to the console
# instead of actually sent.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
