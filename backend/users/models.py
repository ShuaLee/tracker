from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .managers import UserManager
from .validators import validate_timezone


class Currency(models.TextChoices):
    """Currencies a user (and their portfolio) can report in. Module-level so
    other apps can use the same list (`from users.models import Currency`)
    until market data owns currencies (PLAN.md step 9)."""

    CAD = "CAD", "Canadian dollar"
    USD = "USD", "US dollar"
    EUR = "EUR", "Euro"
    GBP = "GBP", "British pound"
    AUD = "AUD", "Australian dollar"
    CHF = "CHF", "Swiss franc"
    JPY = "JPY", "Japanese yen"


class User(AbstractBaseUser, PermissionsMixin):
    """Email is the login; there is no username. Personal details live on
    Profile, billing state on Subscription."""

    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    # Set by the verify-email flow; unverified users can still log in.
    email_verified_at = models.DateTimeField(null=True, blank=True)
    # Set on password change and reset.
    password_changed_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []  # createsuperuser asks for email + password only

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email).lower()

    def save(self, *args, **kwargs):
        # Emails are stored lower-cased however the user was created
        # (manager, admin form, shell, fixture).
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    @property
    def is_email_verified(self):
        return self.email_verified_at is not None


class Profile(models.Model):
    """The user's own settings. Created automatically with the user."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name="profile")
    display_name = models.CharField(max_length=150, blank=True)
    base_currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.CAD)
    timezone = models.CharField(max_length=64, default="America/Toronto", validators=[validate_timezone])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.user.email


class Plan(models.Model):
    """A pricing tier and what it allows (PLAN.md 2.11). Plans are rows, not
    code, so they can be added and re-priced in admin. Feature code never
    checks a plan's name - it reads `users.entitlements.entitlements(user)`.

    `entitlements` holds limits and feature flags, e.g.
    {"max_holdings": 100, "max_sheets": 3, "live_prices": false}. Nothing is
    enforced yet (PLAN.md step 11); keys are added as features land.
    """

    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    entitlements = models.JSONField(default=dict, blank=True)
    # The plan every new user starts on (Free). Exactly one.
    is_default = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["is_default"], condition=Q(is_default=True), name="one_default_plan"),
        ]

    def __str__(self):
        return self.name


class Subscription(models.Model):
    """Which plan a user is on. One per user; everyone starts on the default
    (Free) plan. Set in admin until billing (Stripe) arrives, which will also
    fill in `status` and `renews_at` and add its own provider ids here."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    renews_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.get_status_display()})"


class SecurityEvent(models.Model):
    """Append-only audit trail of account security events. Written only by
    users/audit.py; read-only in admin; each user can read their own."""

    class Event(models.TextChoices):
        REGISTER = "register", "Registered"
        LOGIN = "login", "Logged in"
        LOGIN_FAILED = "login_failed", "Failed login"
        LOGOUT = "logout", "Logged out"
        LOGOUT_ALL = "logout_all", "Logged out everywhere"
        LOCKED = "locked", "Locked out"
        PASSWORD_CHANGED = "password_changed", "Password changed"
        PASSWORD_RESET_REQUESTED = "password_reset_requested", "Password reset requested"
        PASSWORD_RESET_DONE = "password_reset_done", "Password reset"
        EMAIL_CHANGED = "email_changed", "Email changed"
        DEACTIVATED = "deactivated", "Deactivated"
        REACTIVATED = "reactivated", "Reactivated"
        ACCOUNT_DELETED = "account_deleted", "Account deleted"

    # Nullable: a failed login for an unknown email has no user, and a
    # deleted account's events outlive it. `email` keeps who it was about.
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="security_events"
    )
    email = models.EmailField(blank=True)
    event = models.CharField(max_length=32, choices=Event.choices)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["event"]),
        ]

    def __str__(self):
        return f"{self.get_event_display()} - {self.email or '(unknown)'} - {self.created_at:%Y-%m-%d %H:%M}"
