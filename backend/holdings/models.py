from django.conf import settings
from django.db import models
from django.db.models import Q

from accounts.models import Profile


class Portfolio(models.Model):
    """The container above everything a user tracks (PLAN.md guardrail 2).

    For now every user has exactly one, created at signup
    (holdings/signals.py) and living as long as the account.

    Who may see or change it is decided by PortfolioAccess rows, never by
    comparing against `owner` directly - see holdings/access.py.
    """

    # PROTECT: a user who still owns portfolios can't be hard-deleted by
    # accident; ownership has to be dealt with first.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_portfolios"
    )
    name = models.CharField(max_length=100)
    # Same list as the profile's currency (one source of truth until
    # marketdata owns currencies in B3).
    base_currency = models.CharField(
        max_length=3, choices=Profile.Currency.choices, default=Profile.Currency.CAD
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return self.name


class PortfolioAccess(models.Model):
    """Who can use a portfolio, and how (PLAN.md 1.4: sharing, not hierarchy).

    Every portfolio has exactly one active owner row, kept in step with
    Portfolio.owner by holdings/services.py. Manager/viewer rows come with
    sharing (B9); the table and checks exist now so B9 is purely additive.
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MANAGER = "manager", "Manager"
        VIEWER = "viewer", "Viewer"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="access")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolio_access"
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "portfolio access"
        verbose_name_plural = "portfolio access"
        ordering = ["portfolio_id", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["portfolio", "user"], name="one_access_row_per_user"),
            models.UniqueConstraint(
                fields=["portfolio"],
                condition=Q(role="owner", status="active"),
                name="one_active_owner_per_portfolio",
            ),
        ]
        indexes = [models.Index(fields=["user", "status"])]

    def __str__(self):
        return f"{self.user} - {self.get_role_display()} of {self.portfolio} ({self.status})"
