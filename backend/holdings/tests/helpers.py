from accounts.models import User
from holdings.models import PortfolioAccess

PASSWORD = "Tr0ub4dor&3xplosive!"


def make_user(email):
    """A user - which, via the signal, also gives them their portfolio."""
    return User.objects.create_user(email=email, password=PASSWORD)


def portfolio_of(user):
    return user.owned_portfolios.get()


def grant(portfolio, user, role, status=PortfolioAccess.Status.ACTIVE):
    """Stand-in for future sharing (B9): a non-owner access row."""
    return PortfolioAccess.objects.create(
        portfolio=portfolio, user=user, role=role, status=status, granted_by=portfolio.owner
    )
