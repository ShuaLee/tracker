"""Writes that must keep Portfolio and PortfolioAccess in step. Everything that
creates a portfolio goes through create_portfolio() (signup signal) or, for
admin's own save path, add_owner_access(). The backfill data migration is the
one exception - migrations can't import app code."""

from django.db import transaction

from .models import Portfolio, PortfolioAccess

DEFAULT_PORTFOLIO_NAME = "My portfolio"


def _profile_currency(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "base_currency", None) or Portfolio._meta.get_field("base_currency").default


def add_owner_access(portfolio):
    """The owner row for a just-saved portfolio. Call inside the same
    transaction that saved it (create_portfolio does; Django admin's
    changeform view is already atomic)."""
    return PortfolioAccess.objects.create(
        portfolio=portfolio,
        user_id=portfolio.owner_id,
        role=PortfolioAccess.Role.OWNER,
        granted_by_id=portfolio.owner_id,
    )


@transaction.atomic
def create_portfolio(owner, name=DEFAULT_PORTFOLIO_NAME, base_currency=None):
    """Create a portfolio plus its owner access row, atomically. Base currency
    defaults to the owner's profile currency."""
    portfolio = Portfolio.objects.create(
        owner=owner, name=name, base_currency=base_currency or _profile_currency(owner)
    )
    add_owner_access(portfolio)
    return portfolio
