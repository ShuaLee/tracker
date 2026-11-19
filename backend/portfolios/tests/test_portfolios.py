from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse

from portfolios.access import accessible_portfolios
from portfolios.models import Portfolio
from users.models import User

PASSWORD = "Tr0ub4dor&3xplosive!"


def make_user(email):
    return User.objects.create_user(email=email, password=PASSWORD)


class PortfolioOnSignupTests(TestCase):
    def test_new_user_gets_exactly_one_portfolio(self):
        user = make_user("new@example.com")
        portfolio = user.portfolios.get()
        self.assertEqual((portfolio.name, portfolio.base_currency), ("My portfolio", "CAD"))

    def test_superuser_gets_one_and_saving_again_adds_none(self):
        root = User.objects.create_superuser(email="root@example.com", password=PASSWORD)
        root.save()
        self.assertEqual(root.portfolios.count(), 1)

    def test_deleting_the_user_deletes_the_portfolio(self):
        user = make_user("bye@example.com")
        user.delete()
        self.assertFalse(Portfolio.objects.exists())


class BaseCurrencyTests(TestCase):
    def test_portfolio_follows_profile_currency(self):
        user = make_user("fx@example.com")
        user.profile.base_currency = "USD"
        user.profile.save()
        self.assertEqual(user.portfolios.get().base_currency, "USD")

    def test_other_users_portfolios_untouched(self):
        a, b = make_user("a@example.com"), make_user("b@example.com")
        a.profile.base_currency = "EUR"
        a.profile.save()
        self.assertEqual(b.portfolios.get().base_currency, "CAD")


class AccessTests(TestCase):
    def setUp(self):
        self.alice = make_user("alice@example.com")
        self.bob = make_user("bob@example.com")

    def test_each_user_sees_only_their_own(self):
        self.assertEqual(list(accessible_portfolios(self.alice)), list(self.alice.portfolios.all()))
        self.assertNotIn(self.bob.portfolios.get(), accessible_portfolios(self.alice))

    def test_anonymous_and_inactive_see_nothing(self):
        self.assertFalse(accessible_portfolios(AnonymousUser()).exists())
        self.alice.is_active = False
        self.alice.save()
        self.assertFalse(accessible_portfolios(self.alice).exists())


class AccountAndExchangeRateTests(TestCase):
    def setUp(self):
        from portfolios.models import Account, ExchangeRate

        self.Account, self.ExchangeRate = Account, ExchangeRate
        self.portfolio = make_user("owner@example.com").portfolios.get()

    def test_account_names_unique_per_portfolio_only(self):
        from django.db import IntegrityError, transaction

        self.Account.objects.create(portfolio=self.portfolio, name="IBKR TFSA", kind="retirement")
        self.Account.objects.create(portfolio=make_user("b@example.com").portfolios.get(), name="IBKR TFSA")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.Account.objects.create(portfolio=self.portfolio, name="IBKR TFSA")

    def test_rate_rules(self):
        from decimal import Decimal

        from django.db import IntegrityError, transaction

        rate = self.ExchangeRate.objects.create(
            portfolio=self.portfolio, from_currency="USD", to_currency="CAD", rate=Decimal("1.37")
        )
        self.assertEqual(str(rate), "1 USD = 1.37 CAD")
        for fields in (
            {"from_currency": "USD", "to_currency": "CAD", "rate": Decimal("1.4")},  # duplicate pair
            {"from_currency": "CAD", "to_currency": "CAD", "rate": Decimal("1")},  # same currency
            {"from_currency": "EUR", "to_currency": "CAD", "rate": Decimal("0")},  # not positive
        ):
            with self.assertRaises(IntegrityError), transaction.atomic():
                self.ExchangeRate.objects.create(portfolio=self.portfolio, **fields)


class AdminTests(TestCase):
    def test_list_and_change_pages_render_and_add_is_disabled(self):
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password=PASSWORD))
        owner = make_user("owner@example.com")
        self.assertContains(self.client.get(reverse("admin:portfolios_portfolio_changelist")), "owner@example.com")
        change = self.client.get(reverse("admin:portfolios_portfolio_change", args=[owner.portfolios.get().pk]))
        self.assertEqual(change.status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:portfolios_portfolio_add")).status_code, 403)
