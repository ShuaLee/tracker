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


class AdminTests(TestCase):
    def test_list_and_change_pages_render_and_add_is_disabled(self):
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password=PASSWORD))
        owner = make_user("owner@example.com")
        self.assertContains(self.client.get(reverse("admin:portfolios_portfolio_changelist")), "owner@example.com")
        change = self.client.get(reverse("admin:portfolios_portfolio_change", args=[owner.portfolios.get().pk]))
        self.assertEqual(change.status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:portfolios_portfolio_add")).status_code, 403)
