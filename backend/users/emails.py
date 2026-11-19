"""
Every outgoing account email, in one place, so the API and the admin actions
send identical messages. Templates: users/templates/users/emails/. In dev the
console backend prints them; prod uses SMTP (config/settings/*.py).
"""

from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import email_verification_token_generator, for_email


def encode_uid(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def _frontend_url(path, **params):
    # urlencode, not string interpolation: "a+b@x.com" would otherwise reach
    # the frontend as "a b@x.com" ("+" means space in a query string).
    return f"{settings.FRONTEND_URL}/{path}?{urlencode(params)}"


def _send(subject, template, context, to):
    body = render_to_string(f"users/emails/{template}", context)
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to])


def send_verification_email(user):
    """Confirms the address the account currently uses."""
    token = email_verification_token_generator.make_token(for_email(user, user.email))
    url = _frontend_url("verify-email", uid=encode_uid(user), email=user.email, token=token)
    display_name = getattr(getattr(user, "profile", None), "display_name", "")
    _send("Verify your email address", "verify_email.txt", {"display_name": display_name, "verify_url": url}, user.email)


def send_password_reset_email(user):
    token = default_token_generator.make_token(user)
    url = _frontend_url("reset-password", uid=encode_uid(user), token=token)
    _send("Reset your password", "password_reset.txt", {"reset_url": url}, user.email)


def send_email_change_confirmation(user, new_email):
    """Sent to the NEW address only - proves the user receives mail there.
    The old address is told once the change actually happens."""
    token = email_verification_token_generator.make_token(for_email(user, new_email))
    url = _frontend_url("verify-email", uid=encode_uid(user), email=new_email, token=token)
    _send("Confirm your new email address", "email_change_confirmation.txt", {"confirm_url": url}, new_email)


def send_email_changed_notice(old_email, new_email):
    _send("Your login email was changed", "email_changed_notice.txt", {"new_email": new_email}, old_email)
