from django.db.models import ProtectedError
from django.test import TestCase

from holdings.models import Portfolio
from holdings.services import create_portfolio

from .helpers import make_user, portfolio_of


class PortfolioOnSignupTests(TestCase):
    def test_new_user_gets_one_portfolio(self):
        user = make_user("new@example.com")
        portfolio = portfolio_of(user)
        self.assertEqual((portfolio.owner, portfolio.name, portfolio.base_currency), (user, "My portfolio", "CAD"))

    def test_two_users_each_get_their_own(self):
        # PLAN.md B1.5: users created in admin each get a profile and a portfolio.
        a, b = make_user("a@example.com"), make_user("b@example.com")
        self.assertNotEqual(portfolio_of(a), portfolio_of(b))

    def test_superuser_gets_one_too(self):
        from accounts.models import User

        root = User.objects.create_superuser(email="root@example.com", password="x" * 20)
        self.assertEqual(root.owned_portfolios.count(), 1)

    def test_saving_an_existing_user_does_not_add_more(self):
        user = make_user("again@example.com")
        user.save()
        self.assertEqual(user.owned_portfolios.count(), 1)

    def test_owner_cannot_be_hard_deleted_while_owning_a_portfolio(self):
        with self.assertRaises(ProtectedError):
            make_user("owner@example.com").delete()


class CreatePortfolioTests(TestCase):
    def setUp(self):
        self.user = make_user("owner@example.com")

    def test_currency_defaults_to_profile_currency(self):
        self.user.profile.base_currency = "USD"
        self.user.profile.save()
        self.assertEqual(create_portfolio(owner=self.user, name="Second").base_currency, "USD")

    def test_explicit_currency_wins(self):
        self.assertEqual(create_portfolio(owner=self.user, base_currency="EUR").base_currency, "EUR")


class BackfillMigrationTests(TestCase):
    def test_gives_portfolio_only_to_users_without_one(self):
        from importlib import import_module

        from django.apps import apps

        backfill = import_module("holdings.migrations.0002_backfill_default_portfolios").backfill

        has_one = make_user("has@example.com")
        orphan = make_user("orphan@example.com")
        orphan.profile.base_currency = "GBP"
        orphan.profile.save()
        Portfolio.objects.filter(owner=orphan).delete()  # simulate a pre-holdings user

        backfill(apps, None)

        self.assertEqual(has_one.owned_portfolios.count(), 1)
        restored = orphan.owned_portfolios.get()
        self.assertEqual((restored.name, restored.base_currency), ("My portfolio", "GBP"))
