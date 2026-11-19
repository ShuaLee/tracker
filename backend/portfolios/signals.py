from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from users.models import Profile

from .models import Portfolio
from .services import create_portfolio


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_portfolio(sender, instance, created, raw=False, **kwargs):
    """Every new user gets their portfolio (PLAN.md step 1). Runs after the
    users app's receiver (INSTALLED_APPS order), so the profile - and its
    currency - already exists. Skipped for fixture loading (raw)."""
    if created and not raw:
        create_portfolio(owner=instance)


@receiver(post_save, sender=Profile)
def follow_profile_currency(sender, instance, raw=False, **kwargs):
    """The portfolio is invisible, so the base currency a user sets in their
    profile is the one their portfolio reports in. Revisit if a user can
    ever have more than one portfolio."""
    if not raw:
        Portfolio.objects.filter(owner_id=instance.user_id).exclude(
            base_currency=instance.base_currency
        ).update(base_currency=instance.base_currency)
