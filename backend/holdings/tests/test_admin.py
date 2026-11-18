from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from holdings.models import Portfolio, PortfolioAccess

from .helpers import PASSWORD, make_user, portfolio_of


class PortfolioAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email="admin@example.com", password=PASSWORD)
        self.client.force_login(self.admin)
        self.owner = make_user("owner@example.com")

    def test_changelist_and_change_page_render_with_access_inline(self):
        self.assertEqual(self.client.get(reverse("admin:holdings_portfolio_changelist")).status_code, 200)
        response = self.client.get(reverse("admin:holdings_portfolio_change", args=[portfolio_of(self.owner).pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "owner@example.com")

    def test_adding_a_portfolio_in_admin_creates_the_owner_row(self):
        response = self.client.post(
            reverse("admin:holdings_portfolio_add"),
            {"owner": self.owner.pk, "name": "Made by staff", "base_currency": "CHF"},
        )
        self.assertEqual(response.status_code, 302, response.content[:2000])
        portfolio = Portfolio.objects.get(name="Made by staff")
        self.assertTrue(
            PortfolioAccess.objects.filter(portfolio=portfolio, user=self.owner, role="owner").exists()
        )

    def test_owner_is_read_only_once_created(self):
        portfolio = portfolio_of(self.owner)
        owner_row = portfolio.access.get()
        other = make_user("other@example.com")
        response = self.client.post(
            reverse("admin:holdings_portfolio_change", args=[portfolio.pk]),
            {
                "owner": other.pk,  # should be ignored - the field is read-only
                "name": "Renamed",
                "base_currency": "CAD",
                # What the browser submits for the (read-only) access inline.
                "access-TOTAL_FORMS": "1",
                "access-INITIAL_FORMS": "1",
                "access-MIN_NUM_FORMS": "0",
                "access-MAX_NUM_FORMS": "1000",
                "access-0-id": str(owner_row.pk),
                "access-0-portfolio": str(portfolio.pk),
            },
        )
        self.assertEqual(response.status_code, 302, response.content[:2000])
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.name, "Renamed")
        self.assertEqual(portfolio.owner, self.owner)

    def test_access_admin_is_read_only(self):
        self.assertEqual(self.client.get(reverse("admin:holdings_portfolioaccess_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:holdings_portfolioaccess_add")).status_code, 403)
