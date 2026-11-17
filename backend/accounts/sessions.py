"""
"End other sessions" / "end all sessions", for the default DB-backed session
backend, which keeps no per-user index. Fine at this app's scale; revisit
(e.g. django-user-sessions, or a cache-backed index keyed by user id) if the
django_session table gets large enough for this full scan to matter.
"""

from django.contrib.sessions.models import Session
from django.utils import timezone

SESSION_KEY = "_auth_user_id"


def _sessions_for_user(user, exclude_session_key=None):
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if str(data.get(SESSION_KEY)) != str(user.pk):
            continue
        if exclude_session_key and session.session_key == exclude_session_key:
            continue
        yield session


def end_other_sessions(user, except_session_key):
    """Keep the current session, delete every other live session for user."""
    for session in list(_sessions_for_user(user, exclude_session_key=except_session_key)):
        session.delete()


def end_all_sessions(user):
    """Delete every live session for user, including the current one if any."""
    for session in list(_sessions_for_user(user)):
        session.delete()
