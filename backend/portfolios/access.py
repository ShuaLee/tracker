"""
The one place portfolio access is decided. Every query for a portfolio - or
anything inside one (holdings, tags, targets, sheets...) - starts from
`accessible_portfolios(user)`; nothing filters on `owner` itself. Child
models scope with `portfolio__in=accessible_portfolios(user)`, so another
user's data is simply absent (a 404), never a 403.
"""

from .models import Portfolio


def accessible_portfolios(user):
    """Portfolios `user` may use: the ones they own. None for anonymous or
    inactive users."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return Portfolio.objects.none()
    return Portfolio.objects.filter(owner=user)
