"""
Email verification / email-change confirmation tokens.

Built like Django's password-reset link: a URL-safe base64 user id plus a
token from a PasswordResetTokenGenerator subclass, carried as query params
in a link to the frontend. That makes them time-limited
(PASSWORD_RESET_TIMEOUT) and single-use (the hash includes mutable user
state, so it stops matching once that state changes).

One addition: the hash also covers the *target* email, sent as a plain
`email` param next to the token. So one token type serves both "confirm the
email I signed up with" and "confirm my new email". The generator reads the
target from a transient `user.pending_verification_email` attribute set by
`for_email()` - nothing is persisted.
"""

from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    key_salt = "users.tokens.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        target_email = getattr(user, "pending_verification_email", user.email)
        verified_marker = user.email_verified_at.isoformat() if user.email_verified_at else ""
        return f"{user.pk}{target_email}{verified_marker}{timestamp}"


email_verification_token_generator = EmailVerificationTokenGenerator()


def for_email(user, target_email):
    """`user` with the transient attribute the generator reads."""
    user.pending_verification_email = target_email
    return user
