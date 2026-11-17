from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model. Email is the login identifier - there is no username."""

    email = models.EmailField(unique=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    # Set once, by the verify-email flow (accounts/views.py VerifyEmailView).
    email_verified_at = models.DateTimeField(null=True, blank=True)
    # Set by password change, reset, and (on creation) left null.
    password_changed_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # createsuperuser prompts for email + password only

    class Meta:
        ordering = ["email"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email).lower()

    def save(self, *args, **kwargs):
        # Belt-and-suspenders: normalize on every save, not just through
        # full_clean() (e.g. admin forms call full_clean(); UserManager
        # already lowercases; this also covers fixtures/scripts/shells).
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    @property
    def is_email_verified(self):
        return self.email_verified_at is not None


class Profile(models.Model):
    """One-to-one account preferences, created automatically for every User."""

    class Role(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        ADVISOR = "advisor", "Advisor"

    class Currency(models.TextChoices):
        CAD = "CAD", "Canadian dollar"
        USD = "USD", "US dollar"
        EUR = "EUR", "Euro"
        GBP = "GBP", "British pound"
        AUD = "AUD", "Australian dollar"
        CHF = "CHF", "Swiss franc"
        JPY = "JPY", "Japanese yen"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True, related_name="profile"
    )
    display_name = models.CharField(max_length=150, blank=True)
    base_currency = models.CharField(
        max_length=3, choices=Currency.choices, default=Currency.CAD
    )
    # Plain CharField - a full IANA zone list isn't baked into DB-level
    # choices (hundreds of entries in every migration). The admin form
    # renders it as a dropdown instead (see accounts/forms.py).
    timezone = models.CharField(max_length=64, default="America/Toronto")
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.INDIVIDUAL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__email"]

    def __str__(self):
        return self.display_name or self.user.email


class SecurityEvent(models.Model):
    """Append-only audit trail. Written by accounts/audit.py, read-only in admin."""

    class Event(models.TextChoices):
        REGISTER = "register", "Register"
        LOGIN = "login", "Login"
        LOGIN_FAILED = "login_failed", "Login failed"
        LOGOUT = "logout", "Logout"
        PASSWORD_CHANGED = "password_changed", "Password changed"
        PASSWORD_RESET_REQUESTED = "password_reset_requested", "Password reset requested"
        PASSWORD_RESET_DONE = "password_reset_done", "Password reset done"
        EMAIL_CHANGED = "email_changed", "Email changed"
        DEACTIVATED = "deactivated", "Deactivated"
        LOCKED = "locked", "Locked"

    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="security_events",
    )
    event = models.CharField(max_length=32, choices=Event.choices)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["event"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        who = self.user.email if self.user_id else "(no user)"
        return f"{self.get_event_display()} - {who} - {self.created_at:%Y-%m-%d %H:%M}"
