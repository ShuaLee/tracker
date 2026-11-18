"""
The one place portfolio access is decided (PLAN.md 1.4 "written once, used
everywhere"). Views, serializers and admin never filter on `owner` or on
access rows themselves - they call these functions. Future sources of access
(sharing B9, organizations B10) are added here and nowhere else.
"""

from django.db.models import OuterRef, Subquery

from .models import Portfolio, PortfolioAccess

Role = PortfolioAccess.Role

# Higher rank includes everything a lower rank may do.
ROLE_RANK = {Role.VIEWER: 1, Role.MANAGER: 2, Role.OWNER: 3}

# What each kind of action needs (PLAN.md 1.4's role table).
READ = Role.VIEWER
EDIT = Role.MANAGER  # edit holdings, targets, pages, portfolio settings
OWN = Role.OWNER  # share / revoke, delete


def roles_at_least(min_role):
    return [role for role, rank in ROLE_RANK.items() if rank >= ROLE_RANK[min_role]]


def has_role(role, min_role):
    """True if `role` (a user's role on a portfolio, or None) meets `min_role`."""
    return role is not None and ROLE_RANK[role] >= ROLE_RANK[min_role]


def _active_rows(user):
    return PortfolioAccess.objects.filter(user=user, status=PortfolioAccess.Status.ACTIVE)


def accessible_portfolios(user, min_role=READ):
    """Portfolios `user` holds an active access row on with at least `min_role`,
    annotated with `my_role`. Every endpoint over portfolios - or anything
    inside one - scopes through this. Anything outside it must look like it
    doesn't exist (404), not like it's forbidden (403)."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return Portfolio.objects.none()

    my_role = _active_rows(user).filter(portfolio=OuterRef("pk")).values("role")[:1]
    return (
        Portfolio.objects.filter(
            pk__in=_active_rows(user).filter(role__in=roles_at_least(min_role)).values("portfolio")
        )
        .annotate(my_role=Subquery(my_role))
        .select_related("owner")
    )


def role_for(user, portfolio):
    """`user`'s active role on `portfolio`, or None."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return None
    return _active_rows(user).filter(portfolio=portfolio).values_list("role", flat=True).first()
