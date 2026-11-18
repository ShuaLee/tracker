from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .services import create_portfolio


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_portfolio(sender, instance, created, raw=False, **kwargs):
    """Every new user gets their one portfolio (PLAN.md B1.1) - whether they
    registered, were created in admin, or by createsuperuser. Skipped for
    fixture loading (raw), which brings its own rows."""
    if created and not raw:
        create_portfolio(owner=instance)
