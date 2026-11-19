from decimal import Decimal
from unittest import mock

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import RestrictedError
from django.test import TestCase

from assets.models import AssetField, AssetType, Holding
from portfolios.models import Account

from .helpers import make_holding, make_user, standard_type


class StandardTypeTests(TestCase):
    def test_standard_types_are_seeded(self):
        keys = list(AssetType.objects.filter(portfolio__isnull=True).values_list("key", flat=True))
        self.assertEqual(
            keys,
            ["stocks", "bonds", "cash", "crypto", "precious_metals", "real_estate", "vehicles", "private_investment"],
        )
        self.assertFalse(standard_type("vehicles").is_investment)
        self.assertTrue(standard_type("stocks").is_priced)
        self.assertFalse(standard_type("real_estate").is_priced)

    def test_standard_names_and_keys_unique(self):
        for fields in ({"name": "Stocks & ETFs"}, {"name": "Other", "key": "stocks"}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                AssetType.objects.create(portfolio=None, **fields)


class CustomTypeTests(TestCase):
    def setUp(self):
        self.portfolio = make_user().portfolios.get()

    def test_users_can_create_their_own_including_a_standard_name(self):
        AssetType.objects.create(portfolio=self.portfolio, name="Watches", is_investment=False)
        AssetType.objects.create(portfolio=self.portfolio, name="Crypto")  # their own "Crypto" is fine
        with self.assertRaises(IntegrityError), transaction.atomic():
            AssetType.objects.create(portfolio=self.portfolio, name="Watches")

    def test_availability(self):
        mine = AssetType.objects.create(portfolio=self.portfolio, name="Watches")
        other = make_user("other@example.com").portfolios.get()
        self.assertTrue(standard_type("stocks").is_available_to(other.pk))
        self.assertTrue(mine.is_available_to(self.portfolio.pk))
        self.assertFalse(mine.is_available_to(other.pk))


class AssetFieldTests(TestCase):
    def setUp(self):
        self.portfolio = make_user().portfolios.get()
        self.watches = AssetType.objects.create(portfolio=self.portfolio, name="Watches")

    def _field(self, name, field_type="text", options=None, asset_type=None, portfolio=None):
        field = AssetField(
            portfolio=portfolio or self.portfolio, asset_type=asset_type or self.watches,
            name=name, field_type=field_type, options=options or [],
        )
        field.full_clean()
        field.save()
        return field

    def test_key_from_name_unique_and_fixed(self):
        a = self._field("Serial No.")
        b = self._field("Serial-No")
        self.assertEqual((a.key, b.key), ("serial_no", "serial_no_2"))
        a.name = "Serial number"
        a.save()
        a.refresh_from_db()
        self.assertEqual(a.key, "serial_no")

    def test_fields_on_a_standard_type_are_private_to_the_portfolio(self):
        other = make_user("other@example.com").portfolios.get()
        mine = self._field("Address", asset_type=standard_type("real_estate"))
        self._field("Address", asset_type=standard_type("real_estate"), portfolio=other)  # no clash
        self.assertEqual(mine.key, "address")

    def test_cannot_add_fields_to_another_portfolios_type(self):
        other = make_user("other@example.com").portfolios.get()
        with self.assertRaises(ValidationError) as ctx:
            self._field("Brand", portfolio=other)
        self.assertIn("asset_type", ctx.exception.message_dict)

    def test_choice_needs_options_and_others_have_none(self):
        with self.assertRaises(ValidationError):
            self._field("Condition", field_type="choice")
        with self.assertRaises(ValidationError):
            self._field("Brand", options=["x"])
        self._field("Condition", field_type="choice", options=["New", "Worn"])

    def test_normalize(self):
        number = self._field("Weight", "number")
        date = self._field("Bought", "date")
        choice = self._field("Condition", "choice", ["New", "Worn"])
        self.assertEqual(number.normalize("12.50"), "12.50")
        self.assertEqual(number.normalize(3), "3")
        self.assertEqual(date.normalize("2024-02-29"), "2024-02-29")
        self.assertEqual(choice.normalize(" New "), "New")
        for field, bad in ((number, "abc"), (number, "NaN"), (date, "29/02/2024"), (choice, "Mint")):
            with self.assertRaises(ValidationError):
                field.normalize(bad)


class HoldingTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.portfolio = self.user.portfolios.get()

    def test_currency_defaults_to_portfolio_base(self):
        self.user.profile.base_currency = "USD"
        self.user.profile.save()
        self.portfolio.refresh_from_db()
        self.assertEqual(make_holding(self.portfolio, current_price=10).currency, "USD")
        self.assertEqual(make_holding(self.portfolio, "EU", current_price=10, currency="EUR").currency, "EUR")

    def test_investment_override(self):
        car = make_holding(self.portfolio, "Car", "vehicles", current_price=1)
        stock = make_holding(self.portfolio, "Stock", current_price=1)
        house = make_holding(self.portfolio, "Home", "real_estate", current_price=1, investment_override="personal")
        rental_car = make_holding(self.portfolio, "Fleet car", "vehicles", current_price=1, investment_override="investment")
        self.assertEqual(
            [h.is_investment for h in (car, stock, house, rental_car)], [False, True, False, True]
        )

    def test_price_updated_at_tracks_price_changes(self):
        holding = make_holding(self.portfolio, current_price=10)
        first = holding.price_updated_at
        self.assertIsNotNone(first)

        holding = Holding.objects.get(pk=holding.pk)
        holding.notes = "no price change"
        holding.save()
        self.assertEqual(holding.price_updated_at, first)

        later = first.replace(year=first.year + 1)
        with mock.patch("assets.models.timezone.now", return_value=later):
            holding.current_price = Decimal("11")
            holding.save(update_fields=["current_price"])
        holding.refresh_from_db()
        self.assertEqual(holding.price_updated_at, later)

        holding.current_price = None
        holding.save()
        self.assertIsNone(holding.price_updated_at)

    def test_rejects_negative_numbers(self):
        for field in ("quantity", "avg_cost", "current_price"):
            with self.assertRaises(ValidationError) as ctx:
                make_holding(self.portfolio, **{field: -1})
            self.assertIn(field, ctx.exception.message_dict)

    def test_rejects_another_portfolios_type_and_account(self):
        other = make_user("other@example.com").portfolios.get()
        their_type = AssetType.objects.create(portfolio=other, name="Theirs")
        their_account = Account.objects.create(portfolio=other, name="Theirs")
        with self.assertRaises(ValidationError) as ctx:
            make_holding(self.portfolio, asset_type=their_type)
        self.assertIn("asset_type", ctx.exception.message_dict)
        with self.assertRaises(ValidationError) as ctx:
            make_holding(self.portfolio, account=their_account)
        self.assertIn("account", ctx.exception.message_dict)

    def test_custom_fields_are_validated_against_the_types_fields(self):
        watches = AssetType.objects.create(portfolio=self.portfolio, name="Watches")
        AssetField.objects.create(portfolio=self.portfolio, asset_type=watches, name="Brand")
        AssetField.objects.create(portfolio=self.portfolio, asset_type=watches, name="Year", field_type="number")

        holding = make_holding(self.portfolio, asset_type=watches, custom_fields={"brand": "Omega", "year": 1969, "notes": ""})
        self.assertEqual(holding.custom_fields, {"brand": "Omega", "year": "1969"})  # normalized, empty dropped

        for bad in ({"colour": "red"}, {"year": "old"}, ["not", "a", "dict"]):
            with self.assertRaises(ValidationError) as ctx:
                make_holding(self.portfolio, "Bad", asset_type=watches, custom_fields=bad)
            self.assertIn("custom_fields", ctx.exception.message_dict)

    def test_deleting_an_account_keeps_its_holdings(self):
        account = Account.objects.create(portfolio=self.portfolio, name="IBKR")
        holding = make_holding(self.portfolio, account=account)
        account.delete()
        holding.refresh_from_db()
        self.assertIsNone(holding.account)

    def test_a_type_in_use_cannot_be_deleted_alone(self):
        watches = AssetType.objects.create(portfolio=self.portfolio, name="Watches")
        make_holding(self.portfolio, asset_type=watches)
        with self.assertRaises(RestrictedError):
            watches.delete()

    def test_deleting_the_user_deletes_everything_including_custom_types(self):
        watches = AssetType.objects.create(portfolio=self.portfolio, name="Watches")
        AssetField.objects.create(portfolio=self.portfolio, asset_type=watches, name="Brand")
        Account.objects.create(portfolio=self.portfolio, name="Safe")
        make_holding(self.portfolio, asset_type=watches)
        make_holding(self.portfolio, "Stock")
        self.user.delete()
        self.assertFalse(Holding.objects.exists())
        self.assertFalse(AssetType.objects.filter(portfolio__isnull=False).exists())
        self.assertEqual(AssetType.objects.count(), 8)  # standard types untouched
