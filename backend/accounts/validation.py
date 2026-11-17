"""
Wraps django.contrib.auth.password_validation.validate_password so the
UserAttributeSimilarityValidator's "email, display_name" check (see
AUTH_PASSWORD_VALIDATORS in settings/base.py) also sees display_name, which
lives on Profile, not User. Django's validator only ever does
getattr(user, attribute_name, None) - it has no idea Profile exists - so we
attach a transient `display_name` attribute to the user object we hand it.
Nothing is persisted; the attribute never touches the database.
"""

from django.contrib.auth.password_validation import validate_password


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
