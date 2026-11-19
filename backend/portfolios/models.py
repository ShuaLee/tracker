from django.conf import settings
from django.db import models
from django.db.models import F, Q

from users.models import Currency


class Portfolio(models.Model):
    """The container everything a user owns hangs off (PLAN.md 2.1).

    Every user gets exactly one, created at signup. It's invisible: the UI
    never mentions portfolios until a feature needs more than one, so there
    is no portfolio API yet. Its base currency follows the user's profile
    (portfolios/signals.py).
    """

    # CASCADE: deleting an account deletes everything it owns.
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolios")
    name = models.CharField(max_length=100)
    base_currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.CAD)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.name} ({self.owner})"


class Account(models.Model):
    """Where a holding is held: "IBKR TFSA", "Tangerine savings", "Home safe"
    (PLAN.md 2.4). Optional on a holding; CSV imports (step 3) go into one."""

    class Kind(models.TextChoices):
        BROKERAGE = "brokerage", "Brokerage"
        RETIREMENT = "retirement", "Registered / retirement"
        BANK = "bank", "Bank"
        CRYPTO = "crypto", "Crypto exchange / wallet"
        PHYSICAL = "physical", "Physical (safe, home)"
        OTHER = "other", "Other"

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="accounts")
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)
    institution = models.CharField(max_length=100, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["portfolio", "name"], name="unique_account_name_per_portfolio"),
        ]

    def __str__(self):
        return f"{self.name} ({self.portfolio.owner})"


class ExchangeRate(models.Model):
    """A manually entered rate: 1 `from_currency` = `rate` `to_currency`.

    Stand-in until market data supplies live FX (PLAN.md step 9). Stored as
    an explicit currency pair, not "rate to base", so rates stay correct if
    the base currency changes; the inverse pair is derived, never stored.
    """

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="exchange_rates")
    from_currency = models.CharField(max_length=3, choices=Currency.choices)
    to_currency = models.CharField(max_length=3, choices=Currency.choices)
    rate = models.DecimalField(max_digits=20, decimal_places=10)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["from_currency", "to_currency"]
        constraints = [
            models.UniqueConstraint(
                fields=["portfolio", "from_currency", "to_currency"], name="unique_rate_pair_per_portfolio"
            ),
            models.CheckConstraint(condition=~Q(from_currency=F("to_currency")), name="rate_pair_differs"),
            models.CheckConstraint(condition=Q(rate__gt=0), name="rate_positive"),
        ]

    def __str__(self):
        return f"1 {self.from_currency} = {self.rate.normalize()} {self.to_currency}"
