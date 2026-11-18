"""
Validation helpers shared by models, serializers and admin forms.

validate_user_password() wraps
django.contrib.auth.password_validation.validate_password so the
UserAttributeSimilarityValidator's "email, display_name" check (see
AUTH_PASSWORD_VALIDATORS in settings/base.py) also sees display_name, which
lives on Profile, not User. Django's validator only ever does
getattr(user, attribute_name, None) - it has no idea Profile exists - so we
attach a transient `display_name` attribute to the user object we hand it.
Nothing is persisted; the attribute never touches the database.
"""

import zoneinfo
from functools import lru_cache

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


@lru_cache(maxsize=1)
def available_timezones():
    """Every IANA zone name this Python knows (system tz database, or the
    `tzdata` package Django pulls in on Windows). Cached - it scans disk."""
    return frozenset(zoneinfo.available_timezones())


def validate_timezone(value):
    """Profile.timezone is a plain CharField (no DB-level choices - see
    models.py), so this is what stops "Not/AZone" from being saved through
    the API and crashing ZoneInfo() wherever the profile timezone is used."""
    if value not in available_timezones():
        raise ValidationError(
            "%(value)s is not a valid IANA timezone (e.g. America/Toronto).",
            code="invalid_timezone",
            params={"value": value},
        )


def validate_user_password(password, user, display_name=None):
    """
    `user` may be unsaved (registration) or an existing instance (change/
    reset). `display_name` overrides whatever user.profile has, for the
    registration case where the profile doesn't exist yet.
    """
    if display_name is None:
        profile = getattr(user, "profile", None)
        display_name = getattr(profile, "display_name", "") if profile else ""

    user.display_name = display_name
    try:
        validate_password(password, user=user)
    finally:
        del user.display_name
