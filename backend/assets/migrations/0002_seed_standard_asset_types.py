"""
The standard asset types every user starts with (PLAN.md 2.3). Users add
their own (Watches, Trading cards) on top. `key` is the stable identifier
CSV import (step 3) maps its `asset_type` column to.

Defaults: everything counts as an investment except Vehicles; a holding can
override that (e.g. the home you live in -> personal). "Priced" types get
automatic prices once market data exists (step 9).
"""

from django.db import migrations

STANDARD_TYPES = [
    # key, name, icon, is_investment, is_priced
    ("stocks", "Stocks & ETFs", "trending-up", True, True),
    ("bonds", "Bonds", "landmark", True, True),
    ("cash", "Cash", "banknote", True, False),
    ("crypto", "Crypto", "bitcoin", True, True),
    ("precious_metals", "Precious metals", "gem", True, False),
    ("real_estate", "Real estate", "home", True, False),
    ("vehicles", "Vehicles", "car", False, False),
    ("private_investment", "Private investment", "briefcase", True, False),
]


def create_standard_types(apps, schema_editor):
    AssetType = apps.get_model("assets", "AssetType")
    for order, (key, name, icon, is_investment, is_priced) in enumerate(STANDARD_TYPES):
        AssetType.objects.update_or_create(
            portfolio=None,
            key=key,
            defaults={
                "name": name,
                "icon": icon,
                "is_investment": is_investment,
                "is_priced": is_priced,
                "sort_order": order * 10,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("assets", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_standard_types, migrations.RunPython.noop),
    ]
