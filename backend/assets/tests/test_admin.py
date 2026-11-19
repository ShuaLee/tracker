from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from assets.models import AssetField, AssetType, Holding
from portfolios.models import ExchangeRate
from users.models import User

from .helpers import PASSWORD, make_holding, make_user, standard_type


class HoldingAdminTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password=PASSWORD))
        self.portfolio = make_user().portfolios.get()
        self.watches = AssetType.objects.create(portfolio=self.portfolio, name="Watches", is_investment=False)
        AssetField.objects.create(portfolio=self.portfolio, asset_type=self.watches, name="Brand")
        AssetField.objects.create(
            portfolio=self.portfolio, asset_type=self.watches, name="Condition", field_type="choice", options=["New", "Worn"]
        )

    def _post(self, url, **fields):
        data = {
            "portfolio": self.portfolio.pk, "asset_type": self.watches.pk, "account": "", "name": "Rolex",
            "symbol": "", "quantity": "1", "avg_cost": "", "current_price": "14500", "currency": "",
            "investment_override": "", "notes": "",
        }
        data.update(fields)
        return self.client.post(url, data)

    def test_add_then_edit_custom_fields(self):
        response = self._post(reverse("admin:assets_holding_add"))
        self.assertEqual(response.status_code, 302, response.content[:3000])
        holding = Holding.objects.get(name="Rolex")
        self.assertEqual(holding.currency, "CAD")

        change_url = reverse("admin:assets_holding_change", args=[holding.pk])
        page = self.client.get(change_url)
        self.assertContains(page, 'name="custom__brand"')
        self.assertContains(page, 'name="custom__condition"')

        response = self._post(change_url, custom__brand="Rolex", custom__condition="Worn")
        self.assertEqual(response.status_code, 302, response.content[:3000])
        holding.refresh_from_db()
        self.assertEqual(holding.custom_fields, {"brand": "Rolex", "condition": "Worn"})

    def test_invalid_choice_is_rejected(self):
        holding = make_holding(self.portfolio, "Rolex", asset_type=self.watches, current_price=1)
        response = self._post(reverse("admin:assets_holding_change", args=[holding.pk]), custom__condition="Mint")
        self.assertEqual(response.status_code, 200)  # form redisplayed with an error
        holding.refresh_from_db()
        self.assertEqual(holding.custom_fields, {})

    def test_changing_type_drops_old_custom_values(self):
        holding = make_holding(self.portfolio, "Rolex", asset_type=self.watches, current_price=1, custom_fields={"brand": "Rolex"})
        response = self._post(
            reverse("admin:assets_holding_change", args=[holding.pk]),
            asset_type=standard_type("private_investment").pk, custom__brand="Rolex",
        )
        self.assertEqual(response.status_code, 302, response.content[:3000])
        holding.refresh_from_db()
        self.assertEqual(holding.custom_fields, {})

    def test_changelist_and_other_admins_render(self):
        make_holding(self.portfolio, "Stock", current_price=10, avg_cost=8, quantity=3)
        changelist = self.client.get(reverse("admin:assets_holding_changelist"))
        self.assertContains(changelist, "Stock")
        self.assertContains(changelist, "30.00")  # value
        for name in ("assets_assettype_changelist", "assets_assetfield_changelist", "portfolios_account_changelist",
                     "portfolios_exchangerate_changelist"):
            self.assertEqual(self.client.get(reverse(f"admin:{name}")).status_code, 200, name)
        portfolio_page = self.client.get(reverse("admin:portfolios_portfolio_change", args=[self.portfolio.pk]))
        self.assertContains(portfolio_page, "Exchange rates")


class PortfolioSummaryAdminTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password=PASSWORD))
        self.portfolio = make_user().portfolios.get()

    def test_shows_totals_and_what_was_left_out(self):
        ExchangeRate.objects.create(portfolio=self.portfolio, from_currency="USD", to_currency="CAD", rate=Decimal("1.5"))
        make_holding(self.portfolio, "US stock", quantity=10, current_price=10, currency="USD")
        make_holding(self.portfolio, "Unpriced thing", "private_investment")
        make_holding(self.portfolio, "Euro bond", "bonds", current_price=100, currency="EUR")

        listing = self.client.get(reverse("admin:assets_portfoliosummary_changelist"))
        self.assertContains(listing, "150.00")
        self.assertContains(listing, "1 unpriced; no rate for EUR")

        page = self.client.get(reverse("admin:assets_portfoliosummary_change", args=[self.portfolio.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Net worth")
        self.assertContains(page, "No current price: Unpriced thing")
        self.assertContains(page, "No exchange rate from EUR to CAD")
        self.assertContains(page, "Stocks &amp; ETFs")  # by-asset-type breakdown

    def test_read_only(self):
        self.assertEqual(self.client.get(reverse("admin:assets_portfoliosummary_add")).status_code, 403)
