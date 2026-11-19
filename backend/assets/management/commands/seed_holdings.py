"""
Fills one user's portfolio with a small, varied set of demo holdings - every
kind of case the valuation handles: a foreign-currency stock, a stock with no
average cost, physical gold, cash, a car (personal), and a user-made
"Watches" type with custom fields. Run after `seed_users`. Idempotent
(updates by name); dev only.
"""

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from assets.models import AssetField, AssetType, Holding
from assets.valuation import money, portfolio_totals
from portfolios.models import Account, ExchangeRate

D = Decimal

ACCOUNTS = [
    # name, kind, institution
    ("IBKR TFSA", Account.Kind.RETIREMENT, "Interactive Brokers"),
    ("Tangerine savings", Account.Kind.BANK, "Tangerine"),
    ("Home safe", Account.Kind.PHYSICAL, ""),
]

HOLDINGS = [
    # name, symbol, type key, account, quantity, avg_cost, current_price, currency
    ("Peabody Energy", "BTU", "stocks", "IBKR TFSA", D("200"), D("18.50"), D("24.10"), "USD"),
    ("Canadian Natural Resources", "CNQ", "stocks", "IBKR TFSA", D("150"), D("41.20"), D("44.75"), "CAD"),
    ("Frontline", "FRO", "stocks", "IBKR TFSA", D("100"), None, D("22.30"), "USD"),
    ("Gold Maple Leaf 1 oz", "", "precious_metals", "Home safe", D("5"), D("2650"), D("3600"), "CAD"),
    ("Savings", "", "cash", "Tangerine savings", D("40000"), None, D("1"), "CAD"),
    ("Toyota RAV4", "", "vehicles", None, D("1"), D("38000"), D("27000"), "CAD"),
]


class Command(BaseCommand):
    help = "Give a user (default alice@example.com) demo accounts and holdings. Dev only."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="alice@example.com")
        parser.add_argument("--force", action="store_true", help="Run even when DEBUG is off.")

    def handle(self, *args, email, force, **options):
        if not settings.DEBUG and not force:
            raise CommandError("DEBUG is off - refusing to create demo holdings. Use --force to override.")
        user = get_user_model().objects.filter(email=email.lower()).first()
        if user is None:
            raise CommandError(f"No user {email} - run seed_users (or pick another --email).")
        portfolio = user.portfolios.get()

        accounts = {}
        for name, kind, institution in ACCOUNTS:
            accounts[name], _ = Account.objects.update_or_create(
                portfolio=portfolio, name=name, defaults={"kind": kind, "institution": institution}
            )
        ExchangeRate.objects.update_or_create(
            portfolio=portfolio, from_currency="USD", to_currency="CAD", defaults={"rate": D("1.37")}
        )

        types = {t.key: t for t in AssetType.objects.filter(portfolio__isnull=True)}
        for name, symbol, type_key, account, quantity, avg_cost, price, currency in HOLDINGS:
            self._upsert(portfolio, name, {
                "symbol": symbol, "asset_type": types[type_key], "account": accounts.get(account),
                "quantity": quantity, "avg_cost": avg_cost, "current_price": price, "currency": currency,
            })

        watches, _ = AssetType.objects.get_or_create(
            portfolio=portfolio, name="Watches", defaults={"icon": "watch", "is_investment": False, "sort_order": 100}
        )
        for field_name, field_type, options in [
            ("Brand", AssetField.FieldType.TEXT, []),
            ("Reference", AssetField.FieldType.TEXT, []),
            ("Condition", AssetField.FieldType.CHOICE, ["New", "Excellent", "Good", "Worn"]),
        ]:
            if not AssetField.objects.filter(portfolio=portfolio, asset_type=watches, name=field_name).exists():
                AssetField.objects.create(
                    portfolio=portfolio, asset_type=watches, name=field_name, field_type=field_type, options=options
                )
        self._upsert(portfolio, "Rolex Submariner", {
            "asset_type": watches, "account": accounts["Home safe"], "quantity": D("1"),
            "avg_cost": D("11000"), "current_price": D("14500"), "currency": "CAD",
            "custom_fields": {"brand": "Rolex", "reference": "126610LN", "condition": "Excellent"},
        })

        totals = portfolio_totals(portfolio)
        self.stdout.write(self.style.SUCCESS(
            f"Done: {totals.holding_count} holdings for {user.email}. "
            f"Net worth {money(totals.net_worth)} {totals.currency} "
            f"(investments {money(totals.investments)}, personal {money(totals.personal)})."
        ))

    def _upsert(self, portfolio, name, fields):
        holding = Holding.objects.filter(portfolio=portfolio, name=name).first() or Holding(portfolio=portfolio, name=name)
        for attr, value in fields.items():
            setattr(holding, attr, value)
        holding.full_clean()
        holding.save()
