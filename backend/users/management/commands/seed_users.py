"""
Creates (or resets) a fixed set of demo users for manual testing, one per
interesting account state. Idempotent, never touches other accounts, and
refuses to run unless DEBUG is on. The dev database isn't committed, so each
machine runs this (plus `createsuperuser`) after `migrate`.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

DEFAULT_PASSWORD = "TestPass123!"

# email, display name, currency, timezone, verified, active
DEMO_USERS = [
    ("alice@example.com", "Alice Chen", "CAD", "America/Toronto", True, True),
    ("bob@example.com", "Bob Martin", "USD", "America/New_York", True, True),
    ("carol@example.com", "Carol Singh", "AUD", "Australia/Sydney", True, True),
    ("dave@example.com", "Dave Unverified", "EUR", "Europe/Berlin", False, True),
    ("erin@example.com", "Erin Inactive", "GBP", "Europe/London", True, False),
]


class Command(BaseCommand):
    help = "Create/reset demo users (alice, bob, carol, dave, erin @example.com). Dev only."

    def add_arguments(self, parser):
        parser.add_argument("--password", default=DEFAULT_PASSWORD, help=f"Default: {DEFAULT_PASSWORD}")
        parser.add_argument("--force", action="store_true", help="Run even when DEBUG is off.")

    def handle(self, *args, password, force, **options):
        if not settings.DEBUG and not force:
            raise CommandError("DEBUG is off - refusing to create demo users. Use --force to override.")

        User = get_user_model()
        now = timezone.now()
        for email, name, currency, tz, verified, active in DEMO_USERS:
            user, created = User.objects.get_or_create(email=email)
            user.is_active = active
            user.email_verified_at = (user.email_verified_at or now) if verified else None
            user.set_password(password)  # bypasses password rules on purpose: throwaway accounts
            user.save()

            profile = user.profile
            profile.display_name, profile.base_currency, profile.timezone = name, currency, tz
            profile.full_clean()
            profile.save()

            state = ", ".join(filter(None, [currency, "verified" if verified else "unverified", None if active else "inactive"]))
            self.stdout.write(f"{'created' if created else 'reset'}  {email}  ({state})")

        self.stdout.write(self.style.SUCCESS(f"Done. Password for all demo users: {password}"))
