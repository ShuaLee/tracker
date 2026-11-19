"""
Settings shared by every environment.

Nothing environment-specific belongs here: secure-vs-relaxed cookie flags,
the email backend, and anything else that must differ between a developer's
machine and a real deployment live in dev.py / prod.py, which both start
with `from .base import *`.
"""

from datetime import timedelta
from pathlib import Path

import environ

# backend/config/settings/base.py -> backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# Silently does nothing if backend/.env doesn't exist (e.g. in CI, or a prod
# host that injects real environment variables instead).
environ.Env.read_env(str(BASE_DIR / ".env"))


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# Where the React SPA lives. Used to build links in emails (verify, reset,
# confirm email change) since those are frontend routes, not backend ones.
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")

# Admin is mounted at this path; moved off the default outside dev so it
# isn't the first thing a scanner finds.
ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")

# Reserved for marketdata (step B3) - declared now so .env.example documents
# it from the start, not used by any code yet.
FMP_API_KEY = env("FMP_API_KEY", default="")

DEFAULT_FROM_EMAIL = env("DJANGO_DEFAULT_FROM_EMAIL", default="noreply@example.com")


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    "axes",
    # Project
    "users.apps.UsersConfig",
    # After users: its post_save receiver (creates the Profile) must run
    # before portfolios' (creates the portfolio in the profile's currency).
    "portfolios.apps.PortfoliosConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Must be last: axes needs to see the response/exception from every
    # other middleware and the view before it can act on a lockout.
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    # Must come first: it wraps ModelBackend and blocks authentication
    # outright once an account/IP combination is locked out.
    "axes.backends.AxesBackend",
    "django.contrib.auth.backends.ModelBackend",
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        # display_name isn't a field on User (it lives on Profile) - see
        # users/validators.py, which attaches it as a transient attribute
        # before calling validate_password() so this still checks it.
        "OPTIONS": {"user_attributes": ["email", "display_name"]},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Shared by the built-in password-reset token and our own email-verification
# token (users/tokens.py).
PASSWORD_RESET_TIMEOUT = 60 * 60  # 1 hour


# ---------------------------------------------------------------------------
# Sessions / cookies (always-on hardening; secure-transport flags are set
# per-environment in dev.py / prod.py since dev usually runs over plain http)
# ---------------------------------------------------------------------------

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 14 days
SESSION_SAVE_EVERY_REQUEST = True  # ...sliding: refreshed on every request

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True


# ---------------------------------------------------------------------------
# CORS / CSRF (the SPA origin only - never CORS_ALLOW_ALL_ORIGINS)
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])


# ---------------------------------------------------------------------------
# django-axes (lockout after repeated failed logins)
# ---------------------------------------------------------------------------

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(hours=1)
# Lock out the specific (account, IP) combination, not either alone, so one
# person mistyping their password repeatedly can't lock out everyone behind
# the same NAT, and a credential-stuffing run across many accounts from one
# IP doesn't lock those accounts out for their real owners.
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
# Explicit even though this is already the library's default (it falls back
# to get_user_model().USERNAME_FIELD) - self-documenting given we're not on
# the usual "username" field.
AXES_USERNAME_FORM_FIELD = "email"
AXES_RESET_ON_SUCCESS = True


# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Only the users.urls endpoints that explicitly set AllowAny are public;
    # everything else requires a session.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Per IP (DRF's ScopedRateThrottle).
        "login": "5/min",
        "register": "5/min",
        "password_reset": "5/min",
        "resend_verification": "5/min",
        # Per submitted email (users.throttling.EmailRateThrottle), however
        # many IPs the caller rotates through.
        "login_email": "10/hour",
        "register_email": "10/hour",
        "password_reset_email": "5/hour",
        "resend_verification_email": "5/hour",
    },
}


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
