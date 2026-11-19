from axes.signals import user_locked_out
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver

from .audit import log_event
from .entitlements import default_plan
from .models import Profile, Subscription, User


@receiver(post_save, sender=User)
def create_profile_and_subscription(sender, instance, created, raw=False, **kwargs):
    """Every new user gets a Profile and starts on the default (Free) plan.
    Skipped for fixture loading (raw), which brings its own rows."""
    if created and not raw:
        Profile.objects.create(user=instance)
        Subscription.objects.create(user=instance, plan=default_plan())


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    log_event("login", request=request, user=user)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if user is not None:  # None when an anonymous request calls logout()
        log_event("logout", request=request, user=user)


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    email = (credentials.get("email") or "").lower()
    user = User.objects.filter(email=email).first() if email else None
    log_event("login_failed", request=request, user=user, email=email)


@receiver(user_locked_out)
def on_locked_out(sender, request, username, ip_address, **kwargs):
    email = (username or "").lower()
    user = User.objects.filter(email=email).first() if email else None
    log_event("locked", request=request, user=user, email=email)
