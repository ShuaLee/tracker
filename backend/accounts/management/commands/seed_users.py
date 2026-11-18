"""
Creates a fixed set of demo users for manual testing, one per interesting
account state. Idempotent: re-running resets each demo user back to its
listed state and password. Never touches any other account.

The dev DB isn't committed, so every machine needs this (plus
`createsuperuser`) after `migrate`. Refuses to run unless DEBUG is on.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

DEFAULT_PASSWORD = "TestPass123!"

# email, display name, role, currency, timezone, verified, active
DEMO_USERS = [
    ("alice@example.com", "Alice Chen", "individual", "CAD", "America/Toronto", True, True),
    ("bob@example.com", "Bob Martin", "individual", "USD", "America/New_York", True, True),
    ("carol@example.com", "Carol Advisor", "advisor", "CAD", "America/Vancouver", True, True),
    ("dave@example.com", "Dave Unverified", "individual", "EUR", "Europe/Berlin", False, True),
    ("erin@example.com", "Erin Inactive", "individual", "GBP", "Europe/London", True, False),
]


class Command(BaseCommand):
    help = "Create/reset demo users (alice, bob, carol, dave, erin @example.com). Dev only."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help=f"Password for every demo user (default: {DEFAULT_PASSWORD}).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Run even when DEBUG is off. Don't, against a real database.",
        )

    def handle(self, *args, password, force, **options):
        if not settings.DEBUG and not force:
            raise CommandError("DEBUG is off - refusing to create demo users. Use --force to override.")

        User = get_user_model()
        now = timezone.now()

        for email, name, role, currency, tz, verified, active in DEMO_USERS:
            user, created = User.objects.get_or_create(email=email)
            user.is_active = active
            if not verified:
                user.email_verified_at = None
            elif user.email_verified_at is None:
                user.email_verified_at = now
            # set_password bypasses AUTH_PASSWORD_VALIDATORS on purpose -
            # these are throwaway dev accounts.
            user.set_password(password)
            user.save()

            profile = user.profile
            profile.display_name = name
            profile.role = role
            profile.base_currency = currency
            profile.timezone = tz
            profile.full_clean()
            profile.save()

            state = ", ".join(
                filter(None, [role, "verified" if verified else "unverified", None if active else "inactive"])
            )
            self.stdout.write(f"{'created' if created else 'reset'}  {email}  ({state})")

        self.stdout.write(self.style.SUCCESS(f"Done. Password for all demo users: {password}"))
