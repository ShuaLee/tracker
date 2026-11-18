from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from holdings.models import Portfolio

from .helpers import PASSWORD, make_user, portfolio_of


class PortfolioAdminTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password=PASSWORD))
        self.owner = make_user("owner@example.com")

    def test_changelist_and_change_page_render(self):
        self.assertContains(self.client.get(reverse("admin:holdings_portfolio_changelist")), "owner@example.com")
        response = self.client.get(reverse("admin:holdings_portfolio_change", args=[portfolio_of(self.owner).pk]))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_add_a_portfolio(self):
        response = self.client.post(
            reverse("admin:holdings_portfolio_add"),
            {"owner": self.owner.pk, "name": "Made by staff", "base_currency": "CHF"},
        )
        self.assertEqual(response.status_code, 302, response.content[:2000])
        self.assertTrue(Portfolio.objects.filter(owner=self.owner, name="Made by staff").exists())

    def test_owner_is_read_only_once_created(self):
        portfolio = portfolio_of(self.owner)
        other = make_user("other@example.com")
        response = self.client.post(
            reverse("admin:holdings_portfolio_change", args=[portfolio.pk]),
            {"owner": other.pk, "name": "Renamed", "base_currency": "CAD"},  # owner should be ignored
        )
        self.assertEqual(response.status_code, 302, response.content[:2000])
        portfolio.refresh_from_db()
        self.assertEqual((portfolio.name, portfolio.owner), ("Renamed", self.owner))
