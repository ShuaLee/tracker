"""
"End other sessions" / "end all sessions" for Django's DB-backed sessions,
which keep no per-user index - so this scans live sessions. Fine at this
app's scale; switch to a session backend with a user index (e.g.
django-user-sessions) if the session table grows large.
"""

from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.utils import timezone


def _sessions_for_user(user, exclude_session_key=None):
    for session in Session.objects.filter(expire_date__gte=timezone.now()).iterator():
        if str(session.get_decoded().get(SESSION_KEY)) != str(user.pk):
            continue
        if exclude_session_key and session.session_key == exclude_session_key:
            continue
        yield session


def end_other_sessions(user, except_session_key):
    """Keep the current session; delete every other live session of `user`."""
    for session in list(_sessions_for_user(user, exclude_session_key=except_session_key)):
        session.delete()


def end_all_sessions(user):
    """Delete every live session of `user`, including the current one."""
    for session in list(_sessions_for_user(user)):
        session.delete()
