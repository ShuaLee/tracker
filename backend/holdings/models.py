from django.conf import settings
from django.db import models

from accounts.models import Profile


class Portfolio(models.Model):
    """The container above everything a user tracks (PLAN.md guardrail 2).

    For now every user has exactly one, created at signup
    (holdings/signals.py) and living as long as the account. Only its owner
    can see or change it - decided in holdings/access.py, never by filtering
    on `owner` in a view, so adding sharing later (B9) is a change there only.
    """

    # PROTECT: a user who still owns a portfolio can't be hard-deleted by
    # accident; it has to be dealt with first.
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
