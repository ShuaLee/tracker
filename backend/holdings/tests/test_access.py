from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from holdings import access

from .helpers import make_user, portfolio_of


class AccessiblePortfoliosTests(TestCase):
    def setUp(self):
        self.alice = make_user("alice@example.com")
        self.bob = make_user("bob@example.com")

    def test_only_own_portfolio(self):
        self.assertEqual(list(access.accessible_portfolios(self.alice)), [portfolio_of(self.alice)])
        self.assertEqual(list(access.accessible_portfolios(self.bob)), [portfolio_of(self.bob)])

    def test_anonymous_and_inactive_users_see_nothing(self):
        self.assertFalse(access.accessible_portfolios(AnonymousUser()).exists())
        self.alice.is_active = False
        self.alice.save()
        self.assertFalse(access.accessible_portfolios(self.alice).exists())
