"""
Every outgoing email in one place, so the public endpoints and the admin
actions (e.g. "send password-reset email") send identically-built messages.
Templates live in accounts/templates/accounts/emails/; EMAIL_BACKEND is the
console backend in dev, SMTP in prod (config/settings/{dev,prod}.py).
"""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import email_verification_token_generator, for_email


def _uid(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def send_verification_email(user):
    """Confirms the address the account was registered/currently sits at."""
    token = email_verification_token_generator.make_token(for_email(user, user.email))
    url = f"{settings.FRONTEND_URL}/verify-email?uid={_uid(user)}&email={user.email}&token={token}"
    body = render_to_string(
        "accounts/emails/verify_email.txt",
        {"display_name": getattr(getattr(user, "profile", None), "display_name", ""), "verify_url": url},
    )
    send_mail("Verify your email address", body, settings.DEFAULT_FROM_EMAIL, [user.email])


def send_password_reset_email(user):
    from django.contrib.auth.tokens import default_token_generator

    token = default_token_generator.make_token(user)
    url = f"{settings.FRONTEND_URL}/reset-password?uid={_uid(user)}&token={token}"
    body = render_to_string("accounts/emails/password_reset.txt", {"reset_url": url})
    send_mail("Reset your password", body, settings.DEFAULT_FROM_EMAIL, [user.email])


def send_email_change_confirmation(user, new_email):
    """Sent to the NEW address only - proves the user can receive mail there.
    The old address is notified separately, at confirmation time (see
    send_email_changed_notice), once the change is actually real."""
    token = email_verification_token_generator.make_token(for_email(user, new_email))
    url = (
        f"{settings.FRONTEND_URL}/verify-email?uid={_uid(user)}"
        f"&email={new_email}&token={token}"
    )
    body = render_to_string("accounts/emails/email_change_confirmation.txt", {"confirm_url": url})
    send_mail("Confirm your new email address", body, settings.DEFAULT_FROM_EMAIL, [new_email])


def send_email_changed_notice(old_email, new_email):
    body = render_to_string("accounts/emails/email_changed_notice.txt", {"new_email": new_email})
    send_mail("Your login email was changed", body, settings.DEFAULT_FROM_EMAIL, [old_email])
