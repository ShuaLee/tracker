from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db.models.signals import post_save
from django.dispatch import receiver

from axes.signals import user_locked_out

from .audit import log_event
from .models import Profile, User


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    log_event("login", request=request, user=user)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    # user is None if an already-anonymous request calls logout() - nothing
    # useful to log in that case.
    if user is not None:
        log_event("logout", request=request, user=user)


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    email = credentials.get("email")
    user = User.objects.filter(email__iexact=email).first() if email else None
    log_event("login_failed", request=request, user=user)


@receiver(user_locked_out)
def on_locked_out(sender, request, username, ip_address, **kwargs):
    user = User.objects.filter(email__iexact=username).first() if username else None
    log_event("locked", request=request, user=user)
