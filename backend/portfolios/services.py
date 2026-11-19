from .models import Portfolio

DEFAULT_PORTFOLIO_NAME = "My portfolio"


def create_portfolio(owner, name=DEFAULT_PORTFOLIO_NAME):
    """A portfolio for `owner`, in their profile's base currency."""
    profile = getattr(owner, "profile", None)
    currency = getattr(profile, "base_currency", None) or Portfolio._meta.get_field("base_currency").default
    return Portfolio.objects.create(owner=owner, name=name, base_currency=currency)
