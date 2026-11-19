from django.conf import settings
from django.db import models

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
