"""
The one place portfolio access is decided (PLAN.md 1.4 "written once, used
everywhere"). Views, serializers and admin never filter on `owner`
themselves - they call this. Today the rule is simply "you own it"; sharing
(B9) or organizations (B10) would add their sources of access here and
nowhere else.
"""

from .models import Portfolio


def accessible_portfolios(user):
    """Portfolios `user` may use. Every endpoint over portfolios - or anything
    inside one - scopes through this. Anything outside it must look like it
    doesn't exist (404), not like it's forbidden (403)."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return Portfolio.objects.none()
    return Portfolio.objects.filter(owner=user)
