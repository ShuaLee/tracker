import datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from portfolios.models import Account, Portfolio
from users.models import Currency

# Positions can be fractional (crypto: 8+ decimals) and prices tiny or huge.
QUANTITY = {"max_digits": 28, "decimal_places": 10}
PRICE = {"max_digits": 28, "decimal_places": 10}
NON_NEGATIVE = [MinValueValidator(Decimal("0"))]


class AssetType(models.Model):
    """What kind of thing a holding is (PLAN.md 2.3).

    Standard types (`portfolio` empty) ship with the app and are shared by
    everyone; users create their own (Watches, Trading cards) in their
    portfolio. A type is investment or personal by default; a holding can
    override it.
    """

    # Empty = a standard type, shared by everyone.
    portfolio = models.ForeignKey(
        Portfolio, null=True, blank=True, on_delete=models.CASCADE, related_name="asset_types"
    )
    # Stable identifier for standard types ("stocks", "crypto"...), used by
    # seeding and by CSV import's `asset_type` column. Blank for user types.
    key = models.SlugField(max_length=50, blank=True)
    name = models.CharField(max_length=100)
    # A short icon name for the frontend (lucide icon names, e.g. "gem").
    icon = models.CharField(max_length=50, blank=True)
    is_investment = models.BooleanField(default=True)
    # Priced automatically from market data once that exists (step 9);
    # otherwise holdings of this type are priced by hand.
    is_priced = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["portfolio", "name"], name="unique_type_name_per_portfolio"),
            # NULLs are distinct in the constraint above, so standard types
            # need their own uniqueness rules.
            models.UniqueConstraint(
                fields=["name"], condition=Q(portfolio__isnull=True), name="unique_standard_type_name"
            ),
            models.UniqueConstraint(
                fields=["key"], condition=Q(portfolio__isnull=True) & ~Q(key=""), name="unique_standard_type_key"
            ),
        ]

    def __str__(self):
        return self.name if self.is_standard else f"{self.name} ({self.portfolio.owner})"

    @property
    def is_standard(self):
        return self.portfolio_id is None

    def is_available_to(self, portfolio_id):
        """Standard types are available to every portfolio; custom types only
        to their own."""
        return self.portfolio_id is None or self.portfolio_id == portfolio_id


class AssetField(models.Model):
    """A custom field on an asset type (Watches -> Brand, Reference,
    Condition). Values live in Holding.custom_fields under `key`.

    Fields belong to a portfolio even when they're on a standard type, so one
    user's "Address" field on Real estate never appears for anyone else.
    """

    class FieldType(models.TextChoices):
        TEXT = "text", "Text"
        NUMBER = "number", "Number"
        DATE = "date", "Date"
        CHOICE = "choice", "Choice (from a list)"

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="asset_fields")
    asset_type = models.ForeignKey(AssetType, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=100)
    # Derived from the name on creation and never changed afterwards, so
    # renaming a field doesn't orphan the values stored under it.
    key = models.SlugField(max_length=50, editable=False)
    field_type = models.CharField(max_length=10, choices=FieldType.choices, default=FieldType.TEXT)
    # For choice fields: the allowed values, e.g. ["New", "Excellent", "Worn"].
    options = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["portfolio", "asset_type", "key"], name="unique_field_key_per_type"),
        ]

    def __str__(self):
        return f"{self.asset_type.name} → {self.name}"

    def clean(self):
        super().clean()
        if self.asset_type_id and self.portfolio_id and not self.asset_type.is_available_to(self.portfolio_id):
            raise ValidationError({"asset_type": "That asset type belongs to another portfolio."})
        if self.field_type == self.FieldType.CHOICE:
            if not (
                isinstance(self.options, list)
                and self.options
                and all(isinstance(option, str) and option.strip() for option in self.options)
            ):
                raise ValidationError({"options": "A choice field needs a list of non-empty options."})
        elif self.options:
            raise ValidationError({"options": "Only choice fields have options."})
        if not self.pk and not slugify(self.name).replace("-", "_"):
            raise ValidationError({"name": "The name needs at least one letter or number."})

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self._unique_key()
        super().save(*args, **kwargs)

    def _unique_key(self):
        base = slugify(self.name).replace("-", "_")[:45] or "field"
        siblings = AssetField.objects.filter(portfolio_id=self.portfolio_id, asset_type_id=self.asset_type_id)
        key, n = base, 2
        while siblings.filter(key=key).exists():
            key, n = f"{base}_{n}", n + 1
        return key

    def normalize(self, value):
        """Validate one value for this field and return its stored (JSON)
        form: text/choice as str, numbers as a decimal string (no float
        rounding), dates as ISO "YYYY-MM-DD". Raises ValidationError."""
        if self.field_type == self.FieldType.NUMBER:
            try:
                number = Decimal(str(value))
            except (InvalidOperation, ValueError):
                raise ValidationError(f"{self.name}: enter a number.")
            if not number.is_finite():
                raise ValidationError(f"{self.name}: enter a number.")
            return str(number)
        if self.field_type == self.FieldType.DATE:
            if isinstance(value, datetime.date):
                return value.isoformat()
            try:
                return datetime.date.fromisoformat(str(value)).isoformat()
            except ValueError:
                raise ValidationError(f"{self.name}: enter a date as YYYY-MM-DD.")
        value = str(value).strip()
        if self.field_type == self.FieldType.CHOICE and value not in self.options:
            raise ValidationError(f"{self.name}: choose one of {', '.join(self.options)}.")
        return value


class Holding(models.Model):
    """Something owned, as a position (PLAN.md 2.2): quantity, average cost
    and current price - the same for COAL as for a watch. Value, cost and
    gain are calculated (assets/valuation.py), never stored.

    Deferred to step 9 (market data): the `instrument` link that prices a
    holding automatically, and `yield_override` for projected income.
    """

    class Classification(models.TextChoices):
        DEFAULT = "", "Use the asset type's default"
        INVESTMENT = "investment", "Investment"
        PERSONAL = "personal", "Personal"

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="holdings")
    # RESTRICT, not PROTECT: a type with holdings can't be deleted on its own,
    # but deleting a whole portfolio (both its custom types and holdings) works.
    asset_type = models.ForeignKey(AssetType, on_delete=models.RESTRICT, related_name="holdings")
    # Deleting an account keeps its holdings, just unassigned.
    account = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.SET_NULL, related_name="holdings"
    )
    name = models.CharField(max_length=200)
    symbol = models.CharField(max_length=30, blank=True)
    quantity = models.DecimalField(**QUANTITY, default=Decimal("1"), validators=NON_NEGATIVE)
    avg_cost = models.DecimalField(
        **PRICE, null=True, blank=True, validators=NON_NEGATIVE, help_text="Average purchase price per unit."
    )
    current_price = models.DecimalField(
        **PRICE, null=True, blank=True, validators=NON_NEGATIVE, help_text="Price per unit now."
    )
    # Set automatically whenever current_price changes, so the user can see
    # how stale a hand-entered price is.
    price_updated_at = models.DateTimeField(null=True, blank=True, editable=False)
    # Blank on input means "the portfolio's base currency" (filled in on save).
    currency = models.CharField(max_length=3, choices=Currency.choices, blank=True)
    investment_override = models.CharField(
        max_length=10, choices=Classification.choices, default=Classification.DEFAULT, blank=True
    )
    custom_fields = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=0), name="holding_quantity_non_negative"),
            models.CheckConstraint(
                condition=Q(avg_cost__isnull=True) | Q(avg_cost__gte=0), name="holding_avg_cost_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(current_price__isnull=True) | Q(current_price__gte=0),
                name="holding_price_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.symbol})" if self.symbol else self.name

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._loaded_price = instance.__dict__.get("current_price")
        return instance

    @property
    def is_investment(self):
        if self.investment_override == self.Classification.INVESTMENT:
            return True
        if self.investment_override == self.Classification.PERSONAL:
            return False
        return self.asset_type.is_investment

    def clean(self):
        super().clean()
        errors = {}
        if self.portfolio_id and self.asset_type_id and not self.asset_type.is_available_to(self.portfolio_id):
            errors["asset_type"] = "That asset type belongs to another portfolio."
        if self.portfolio_id and self.account_id and self.account.portfolio_id != self.portfolio_id:
            errors["account"] = "That account belongs to another portfolio."
        if errors:
            raise ValidationError(errors)
        if self.portfolio_id and self.asset_type_id:
            self.custom_fields = self._clean_custom_fields()

    def _clean_custom_fields(self):
        if not isinstance(self.custom_fields, dict):
            raise ValidationError({"custom_fields": "Custom fields must be an object of field key → value."})
        fields = {f.key: f for f in self.available_fields()}
        # Empty means "not set", so empty values are simply dropped.
        values = {key: value for key, value in self.custom_fields.items() if value not in (None, "")}
        unknown = set(values) - set(fields)
        if unknown:
            raise ValidationError(
                {"custom_fields": f"Not fields of {self.asset_type.name}: {', '.join(sorted(unknown))}."}
            )
        cleaned, problems = {}, []
        for key, value in values.items():
            try:
                cleaned[key] = fields[key].normalize(value)
            except ValidationError as exc:
                problems.extend(exc.messages)
        if problems:
            raise ValidationError({"custom_fields": problems})
        return cleaned

    def available_fields(self):
        """The custom fields this holding can have: its portfolio's fields
        on its asset type."""
        return AssetField.objects.filter(portfolio_id=self.portfolio_id, asset_type_id=self.asset_type_id)

    def save(self, *args, **kwargs):
        if not self.currency:
            self.currency = self.portfolio.base_currency
        if self.current_price != getattr(self, "_loaded_price", None):
            self.price_updated_at = timezone.now() if self.current_price is not None else None
            update_fields = kwargs.get("update_fields")
            if update_fields is not None and "current_price" in update_fields:
                kwargs["update_fields"] = {*update_fields, "price_updated_at"}
        super().save(*args, **kwargs)
        self._loaded_price = self.current_price


class PortfolioSummary(Portfolio):
    """Proxy so the admin can show a portfolio's totals (net worth,
    investments, gain) next to its holdings. Lives here, not in portfolios,
    because the totals need assets.valuation and portfolios may not import
    assets (PLAN.md 3)."""

    class Meta:
        proxy = True
        verbose_name = "portfolio summary"
        verbose_name_plural = "portfolio summaries"
