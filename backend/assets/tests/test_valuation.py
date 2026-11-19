"""
The calculation layer. Pure-function tests use lightweight stand-ins (no
database); the last class runs the same rules end-to-end through
portfolio_totals() and the seed_holdings command.
"""

from decimal import Decimal
from io import StringIO
from types import SimpleNamespace

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, TestCase, override_settings

from assets import valuation
from assets.valuation import Rates, holding_cost, holding_gain, holding_value, money, totals, value_by
from portfolios.models import ExchangeRate
from users.models import User

from .helpers import make_holding, make_user

D = Decimal


def h(quantity="1", price=None, cost=None, currency="CAD", investment=True, type_name="Stocks", account=None):
    """A stand-in holding: just the attributes valuation reads."""
    return SimpleNamespace(
        quantity=D(quantity),
        current_price=None if price is None else D(price),
        avg_cost=None if cost is None else D(cost),
        currency=currency,
        is_investment=investment,
        asset_type=SimpleNamespace(name=type_name),
        account=account,
    )


class HoldingMathTests(SimpleTestCase):
    def test_value_cost_gain(self):
        holding = h("200", price="24.10", cost="18.50")
        self.assertEqual(holding_value(holding), D("4820.00"))
        self.assertEqual(holding_cost(holding), D("3700.00"))
        self.assertEqual(holding_gain(holding), D("1120.00"))

    def test_missing_inputs_give_none_not_zero(self):
        self.assertIsNone(holding_value(h(cost="5")))
        self.assertIsNone(holding_cost(h(price="5")))
        self.assertIsNone(holding_gain(h(price="5")))
        self.assertIsNone(holding_gain(h(cost="5")))

    def test_decimal_precision_is_kept(self):
        btc = h("0.00012345", price="98765.4321")
        self.assertEqual(holding_value(btc), D("0.00012345") * D("98765.4321"))
        self.assertEqual(money(D("12.345")), D("12.35"))
        self.assertIsNone(money(None))


class RatesTests(SimpleTestCase):
    def test_same_direct_inverse_missing(self):
        rates = Rates({("USD", "CAD"): D("1.25")})
        self.assertEqual(rates.convert(D("10"), "CAD", "CAD"), D("10"))
        self.assertEqual(rates.convert(D("10"), "USD", "CAD"), D("12.50"))
        self.assertEqual(rates.convert(D("12.50"), "CAD", "USD"), D("10"))
        self.assertIsNone(rates.convert(D("10"), "EUR", "CAD"))


class TotalsTests(SimpleTestCase):
    def setUp(self):
        self.rates = Rates({("USD", "CAD"): D("1.37")})

    def test_mixed_portfolio(self):
        holdings = [
            h("200", price="24.10", cost="18.50", currency="USD"),  # 6603.40 CAD, cost 5069.00
            h("150", price="44.75", cost="41.20"),  # 6712.50, cost 6180.00
            h("1", price="27000", cost="38000", investment=False),  # car: personal, loss 11000
        ]
        t = totals(holdings, "CAD", self.rates)
        self.assertEqual(t.investments, D("13315.90"))
        self.assertEqual(t.personal, D("27000"))
        self.assertEqual(t.net_worth, D("40315.90"))
        self.assertEqual(t.cost_basis, D("49249.00"))
        self.assertEqual(t.unrealized_gain, D("-8933.10"))
        self.assertEqual(t.holding_count, 3)
        self.assertTrue(t.is_complete)

    def test_gain_only_counts_holdings_with_a_cost(self):
        t = totals([h("10", price="5", cost="4"), h("10", price="100")], "CAD", self.rates)
        self.assertEqual(t.net_worth, D("1050"))
        self.assertEqual(t.cost_basis, D("40"))
        self.assertEqual(t.unrealized_gain, D("10"))

    def test_unpriced_and_unconvertible_are_left_out_and_reported(self):
        unpriced = h("3", cost="10")
        euro = h("1", price="100", currency="EUR")
        t = totals([unpriced, euro, h("1", price="50")], "CAD", self.rates)
        self.assertEqual(t.net_worth, D("50"))
        self.assertEqual(t.cost_basis, D("0"))
        self.assertEqual(t.unpriced, [unpriced])
        self.assertEqual(t.missing_rates, {"EUR"})
        self.assertFalse(t.is_complete)

    def test_empty(self):
        t = totals([], "USD", self.rates)
        self.assertEqual((t.net_worth, t.holding_count, t.currency), (D("0"), 0, "USD"))

    def test_value_by_groups_largest_first(self):
        holdings = [
            h("1", price="10", type_name="Cash"),
            h("1", price="100", currency="USD", type_name="Stocks"),
            h("1", price="5", type_name="Cash"),
            h("1", type_name="Gold"),  # unpriced: skipped
        ]
        grouped = value_by(holdings, "CAD", self.rates, lambda x: x.asset_type.name)
        self.assertEqual(list(grouped.items()), [("Stocks", D("137.00")), ("Cash", D("15"))])


class PortfolioTotalsTests(TestCase):
    """Through the database: the PLAN step 2 'done when'."""

    def test_portfolio_totals_use_its_own_holdings_and_rates(self):
        portfolio = make_user().portfolios.get()
        other = make_user("other@example.com").portfolios.get()
        ExchangeRate.objects.create(portfolio=portfolio, from_currency="USD", to_currency="CAD", rate=D("1.40"))
        make_holding(portfolio, "US stock", quantity=10, current_price=100, avg_cost=90, currency="USD")
        make_holding(portfolio, "Car", "vehicles", current_price=20000)
        make_holding(other, "Not mine", current_price=999999)

        t = valuation.portfolio_totals(portfolio)
        self.assertEqual(t.investments, D("1400"))
        self.assertEqual(t.personal, D("20000"))
        self.assertEqual(t.net_worth, D("21400"))
        self.assertEqual(t.cost_basis, D("1260"))
        self.assertEqual(t.unrealized_gain, D("140"))

    def test_base_currency_change_reconverts(self):
        user = make_user()
        portfolio = user.portfolios.get()
        ExchangeRate.objects.create(portfolio=portfolio, from_currency="USD", to_currency="CAD", rate=D("1.25"))
        make_holding(portfolio, "CAD cash", "cash", quantity=125, current_price=1)
        user.profile.base_currency = "USD"
        user.profile.save()
        portfolio.refresh_from_db()
        self.assertEqual(valuation.portfolio_totals(portfolio).net_worth, D("100"))

    @override_settings(DEBUG=True)
    def test_seed_holdings_totals_match_the_hand_calculation(self):
        make_user("alice@example.com")
        call_command("seed_holdings", stdout=StringIO())
        call_command("seed_holdings", stdout=StringIO())  # idempotent
        portfolio = User.objects.get(email="alice@example.com").portfolios.get()
        t = valuation.portfolio_totals(portfolio)
        self.assertEqual(t.holding_count, 7)
        self.assertEqual(money(t.investments), D("74371.00"))
        self.assertEqual(money(t.personal), D("41500.00"))
        self.assertEqual(money(t.net_worth), D("115871.00"))
        self.assertEqual(money(t.cost_basis), D("73499.00"))
        self.assertEqual(money(t.unrealized_gain), D("-683.10"))
        rolex = portfolio.holdings.get(name="Rolex Submariner")
        self.assertEqual(rolex.custom_fields["condition"], "Excellent")

    @override_settings(DEBUG=False)
    def test_seed_holdings_refuses_without_debug(self):
        with self.assertRaises(CommandError):
            call_command("seed_holdings", stdout=StringIO())
