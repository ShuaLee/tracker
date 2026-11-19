"""
Validators shared by models, serializers and admin forms.

`validate_user_password()` wraps Django's validate_password so the
UserAttributeSimilarityValidator (configured with "email, display_name" in
settings) also sees `display_name`, which lives on Profile, not User. Django's
validator only does getattr(user, name), so a transient attribute is attached
to the user object for the duration of the call; nothing is persisted.
"""

import zoneinfo
from functools import lru_cache

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


def validate_user_password(password, user, display_name=None):
    """`user` may be unsaved (registration) or existing (change / reset).
    `display_name` overrides user.profile's, for registration, where the
    profile doesn't exist yet."""
    if display_name is None:
        profile = getattr(user, "profile", None)
        display_name = getattr(profile, "display_name", "") if profile else ""

    user.display_name = display_name
    try:
        validate_password(password, user=user)
    finally:
        del user.display_name


@lru_cache(maxsize=1)
def available_timezones():
    """Every IANA zone name this Python knows (system tz database, or the
    `tzdata` package Django pulls in on Windows). Cached - it scans disk."""
    return frozenset(zoneinfo.available_timezones())


def validate_timezone(value):
    """Profile.timezone is a plain CharField (no DB-level choices: ~600 zones
    would be baked into every migration), so this is what keeps it valid."""
    if value not in available_timezones():
        raise ValidationError(
            "%(value)s is not a valid IANA timezone (e.g. America/Toronto).",
            code="invalid_timezone",
            params={"value": value},
        )
