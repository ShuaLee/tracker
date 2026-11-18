"""Portfolio writes. Everything that creates a portfolio goes through
create_portfolio() (the signup signal today) so the currency default lives in
one place. The backfill data migration mirrors it - migrations can't import
app code."""

from .models import Portfolio

DEFAULT_PORTFOLIO_NAME = "My portfolio"


def _profile_currency(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "base_currency", None) or Portfolio._meta.get_field("base_currency").default


def create_portfolio(owner, name=DEFAULT_PORTFOLIO_NAME, base_currency=None):
    """Create a portfolio. Base currency defaults to the owner's profile currency."""
    return Portfolio.objects.create(
        owner=owner, name=name, base_currency=base_currency or _profile_currency(owner)
    )
