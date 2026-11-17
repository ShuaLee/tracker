"""Writes accounts.models.SecurityEvent rows. The only place that should."""

from .models import SecurityEvent


def get_client_ip(request):
    if request is None:
        return None
    # REMOTE_ADDR only - a request header like X-Forwarded-For is
    # attacker-controlled unless a trusted reverse proxy strips/sets it,
    # which isn't configured here.
    return request.META.get("REMOTE_ADDR")


def get_user_agent(request):
    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")[:255]


def log_event(event, request=None, user=None):
    """Record one SecurityEvent. `user` may be None (e.g. a failed login
    with an email that doesn't match any account)."""
    SecurityEvent.objects.create(
        user=user,
        event=event,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
