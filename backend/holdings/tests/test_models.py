from django.db import IntegrityError, transaction
from django.test import TestCase

from holdings.models import Portfolio, PortfolioAccess
from holdings.services import create_portfolio

from .helpers import grant, make_user, portfolio_of


class PortfolioOnSignupTests(TestCase):
    def test_new_user_gets_one_portfolio_and_owner_row(self):
        user = make_user("new@example.com")
        portfolio = portfolio_of(user)
        self.assertEqual((portfolio.name, portfolio.base_currency), ("My portfolio", "CAD"))
        row = PortfolioAccess.objects.get(portfolio=portfolio)
        self.assertEqual((row.user, row.role, row.status), (user, "owner", "active"))

    def test_two_users_each_get_their_own(self):
        # PLAN.md B1.5: users created in admin each get a profile, a default
        # portfolio and an owner access row.
        a, b = make_user("a@example.com"), make_user("b@example.com")
        self.assertNotEqual(portfolio_of(a), portfolio_of(b))
        self.assertEqual(PortfolioAccess.objects.filter(role="owner").count(), 2)

    def test_superuser_gets_one_too(self):
        from accounts.models import User

        root = User.objects.create_superuser(email="root@example.com", password="x" * 20)
        self.assertEqual(root.owned_portfolios.count(), 1)

    def test_saving_an_existing_user_does_not_add_more(self):
        user = make_user("again@example.com")
        user.save()
        self.assertEqual(user.owned_portfolios.count(), 1)


class CreatePortfolioTests(TestCase):
    def setUp(self):
        self.user = make_user("owner@example.com")

    def test_currency_defaults_to_profile_currency(self):
        self.user.profile.base_currency = "USD"
        self.user.profile.save()
        self.assertEqual(create_portfolio(owner=self.user, name="Second").base_currency, "USD")

    def test_explicit_currency_wins(self):
        self.assertEqual(create_portfolio(owner=self.user, base_currency="EUR").base_currency, "EUR")

    def test_creates_matching_owner_row(self):
        portfolio = create_portfolio(owner=self.user, name="Second")
        self.assertTrue(
            PortfolioAccess.objects.filter(portfolio=portfolio, user=self.user, role="owner").exists()
        )


class ConstraintTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.portfolio = portfolio_of(self.owner)

    def test_only_one_active_owner_row(self):
        other = make_user("other@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            grant(self.portfolio, other, PortfolioAccess.Role.OWNER)

    def test_revoked_owner_rows_do_not_count_toward_the_limit(self):
        other = make_user("former@example.com")
        grant(self.portfolio, other, PortfolioAccess.Role.OWNER, status=PortfolioAccess.Status.REVOKED)

    def test_one_row_per_user_per_portfolio(self):
        viewer = make_user("viewer@example.com")
        grant(self.portfolio, viewer, PortfolioAccess.Role.VIEWER)
        with self.assertRaises(IntegrityError), transaction.atomic():
            grant(self.portfolio, viewer, PortfolioAccess.Role.MANAGER)

    def test_owner_cannot_be_hard_deleted_while_owning_portfolios(self):
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            self.owner.delete()

    def test_deleting_a_portfolio_cascades_its_access_rows(self):
        # Only staff can delete (admin); the API has no delete.
        self.portfolio.delete()
        self.assertFalse(PortfolioAccess.objects.filter(portfolio_id=self.portfolio.pk).exists())


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
        self.assertEqual(restored.base_currency, "GBP")
        self.assertTrue(PortfolioAccess.objects.filter(portfolio=restored, user=orphan, role="owner").exists())
