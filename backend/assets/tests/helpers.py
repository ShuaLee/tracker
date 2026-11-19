from decimal import Decimal

from assets.models import AssetType, Holding
from users.models import User

PASSWORD = "Tr0ub4dor&3xplosive!"


def make_user(email="owner@example.com"):
    """A user - and, via signals, their profile and portfolio."""
    return User.objects.create_user(email=email, password=PASSWORD)


def standard_type(key):
    return AssetType.objects.get(portfolio__isnull=True, key=key)


def make_holding(portfolio, name="Holding", type_key="stocks", **fields):
    fields.setdefault("asset_type", standard_type(type_key))
    for decimal_field in ("quantity", "avg_cost", "current_price"):
        if isinstance(fields.get(decimal_field), (int, str)):
            fields[decimal_field] = Decimal(str(fields[decimal_field]))
    holding = Holding(portfolio=portfolio, name=name, **fields)
    holding.full_clean()
    holding.save()
    return holding
