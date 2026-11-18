from accounts.models import User

PASSWORD = "Tr0ub4dor&3xplosive!"


def make_user(email):
    """A user - which, via the signal, also gives them their portfolio."""
    return User.objects.create_user(email=email, password=PASSWORD)


def portfolio_of(user):
    return user.owned_portfolios.get()
