"""
Creates the Free plan every new user starts on (PLAN.md 2.11). Paid plans
(Plus / Pro) are added in admin once their limits are decided.
"""

from django.db import migrations


def create_free_plan(apps, schema_editor):
    Plan = apps.get_model("users", "Plan")
    Plan.objects.get_or_create(
        slug="free",
        defaults={"name": "Free", "is_default": True, "sort_order": 0, "entitlements": {}},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_free_plan, migrations.RunPython.noop),
    ]
