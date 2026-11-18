"""
Give every user who existed before holdings was installed the portfolio that
new users get from the post_save receiver (holdings/signals.py). Mirrors
holdings.services.create_portfolio - a migration must use historical models,
so it can't call the service itself.

Reverse is a no-op: unapplying 0001 drops the table anyway.
"""

from django.conf import settings
from django.db import migrations

DEFAULT_PORTFOLIO_NAME = "My portfolio"  # = services.DEFAULT_PORTFOLIO_NAME at the time of writing


def backfill(apps, schema_editor):
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)
    Profile = apps.get_model("accounts", "Profile")
    Portfolio = apps.get_model("holdings", "Portfolio")

    currencies = dict(Profile.objects.values_list("user_id", "base_currency"))
    Portfolio.objects.bulk_create(
        Portfolio(owner=user, name=DEFAULT_PORTFOLIO_NAME, base_currency=currencies.get(user.pk, "CAD"))
        for user in User.objects.filter(owned_portfolios__isnull=True)
    )


class Migration(migrations.Migration):
    dependencies = [
        ("holdings", "0001_initial"),
        ("accounts", "0002_profile_timezone_validator_security_events"),
    ]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
