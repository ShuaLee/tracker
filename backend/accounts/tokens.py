"""
Email verification / email-change confirmation tokens.

Built the same way Django's own password-reset link is: a user id
(uidb64, URL-safe base64) plus a token from a PasswordResetTokenGenerator
subclass, carried as query params in a link to the frontend. That gives us,
for free, the same properties PLAN.md asks for - time-limited
(PASSWORD_RESET_TIMEOUT) and single-use (the hash is derived from mutable
user state, so it stops matching once that state changes).

The one addition over the stock generator: the hash also incorporates the
*target* email, carried as an explicit `email` query param alongside the
token (not secret - it's the address the recipient already received this
link at). That lets one token/endpoint serve both "confirm the email I
registered with" and "confirm my new email": EmailVerificationTokenGenerator
reads the target off a transient `user.pending_verification_email`
attribute that the caller sets before calling make_token()/check_token(),
exactly like the UserAttributeSimilarityValidator trick in validation.py.
"""

from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        target_email = getattr(user, "pending_verification_email", user.email)
        verified_marker = user.email_verified_at.isoformat() if user.email_verified_at else ""
        return f"{user.pk}{target_email}{verified_marker}{timestamp}"


email_verification_token_generator = EmailVerificationTokenGenerator()


def for_email(user, target_email):
    """Return a `user` with the transient attribute the generator reads,
    without mutating anything persisted."""
    user.pending_verification_email = target_email
    return user
