"""Writes users.models.SecurityEvent rows. The only place that should."""

from .models import SecurityEvent


def get_client_ip(request):
    if request is None:
        return None
    # REMOTE_ADDR only: X-Forwarded-For is attacker-controlled unless a
    # trusted reverse proxy sets it, and none is configured.
    return request.META.get("REMOTE_ADDR")


def get_user_agent(request):
    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")[:255]


def log_event(event, request=None, user=None, email=""):
    """Record one SecurityEvent. Pass `request=None` for events triggered by
    staff in admin, so the staff member's IP isn't recorded against the
    target account. `email` defaults to the user's."""
    SecurityEvent.objects.create(
        user=user,
        email=email or (user.email if user is not None else ""),
        event=event,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
