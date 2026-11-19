from axes.utils import reset as axes_reset
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.html import format_html

from . import emails
from .audit import log_event
from .forms import ProfileInlineForm, UserChangeForm, UserCreationForm
from .models import Plan, Profile, SecurityEvent, Subscription, User
from .sessions import end_all_sessions

admin.site.site_header = "Personal Wealth admin"
admin.site.site_title = "Personal Wealth admin"
admin.site.index_title = "Administration"


class EmailVerifiedFilter(admin.SimpleListFilter):
    title = "email verified"
    parameter_name = "email_verified"

    def lookups(self, request, model_admin):
        return [("yes", "Yes"), ("no", "No")]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(email_verified_at__isnull=False)
        if self.value() == "no":
            return queryset.filter(email_verified_at__isnull=True)
        return queryset


class ProfileInline(admin.StackedInline):
    model = Profile
    form = ProfileInlineForm
    can_delete = False


class SubscriptionInline(admin.StackedInline):
    """Staff set plans here until billing exists (PLAN.md 2.11)."""

    model = Subscription
    can_delete = False
    fields = ["plan", "status", "renews_at", "created_at", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    inlines = [ProfileInline, SubscriptionInline]

    list_display = [
        "email",
        "display_name_column",
        "plan_column",
        "is_active",
        "is_staff",
        "email_verified_badge",
        "last_login",
        "date_joined",
    ]
    list_filter = ["subscription__plan", "is_active", "is_staff", EmailVerifiedFilter]
    search_fields = ["email", "profile__display_name"]
    ordering = ["email"]
    list_per_page = 50
    readonly_fields = ["last_login", "date_joined", "password_changed_at", "email_verified_at"]

    fieldsets = (
        ("Account", {"fields": ("email", "password")}),
        ("Verification & security", {"fields": ("email_verified_at", "password_changed_at", "last_login", "date_joined")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)

    actions = [
        "deactivate_users",
        "reactivate_users",
        "mark_email_verified",
        "send_password_reset",
        "unlock_users",
        "end_sessions",
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("profile", "subscription__plan")

    def get_inline_instances(self, request, obj=None):
        # Profile and Subscription are created by the post_save signal once
        # the user exists; an inline on the add page would race it.
        return [] if obj is None else super().get_inline_instances(request, obj)

    @admin.display(description="Display name", ordering="profile__display_name")
    def display_name_column(self, obj):
        return obj.profile.display_name or "—"

    @admin.display(description="Plan", ordering="subscription__plan__sort_order")
    def plan_column(self, obj):
        subscription = getattr(obj, "subscription", None)
        return subscription.plan.name if subscription else "—"

    @admin.display(description="Email verified")
    def email_verified_badge(self, obj):
        if obj.is_email_verified:
            return format_html('<span style="color:#1a7f37;font-weight:600;">&#10003; verified</span>')
        return format_html('<span style="color:#b42318;font-weight:600;">&#10007; unverified</span>')

    # Audit rows from admin actions pass request=None: the request is the
    # staff member's, and their IP shouldn't be recorded against the user.

    @admin.action(description="Deactivate selected users (and end their sessions)")
    def deactivate_users(self, request, queryset):
        users = list(queryset.filter(is_active=True))
        for user in users:
            user.is_active = False
            user.save(update_fields=["is_active"])
            end_all_sessions(user)
            log_event("deactivated", user=user)
        self.message_user(request, f"Deactivated {len(users)} user(s).", messages.SUCCESS)

    @admin.action(description="Reactivate selected users")
    def reactivate_users(self, request, queryset):
        users = list(queryset.filter(is_active=False))
        for user in users:
            user.is_active = True
            user.save(update_fields=["is_active"])
            log_event("reactivated", user=user)
        self.message_user(request, f"Reactivated {len(users)} user(s).", messages.SUCCESS)

    @admin.action(description="Mark email verified")
    def mark_email_verified(self, request, queryset):
        updated = queryset.filter(email_verified_at__isnull=True).update(email_verified_at=timezone.now())
        self.message_user(request, f"Marked {updated} user(s) as verified.", messages.SUCCESS)

    @admin.action(description="Send password-reset email")
    def send_password_reset(self, request, queryset):
        users = list(queryset)
        for user in users:
            emails.send_password_reset_email(user)
        self.message_user(request, f"Sent {len(users)} password-reset email(s).", messages.SUCCESS)

    @admin.action(description="Unlock (clear failed-login lockout)")
    def unlock_users(self, request, queryset):
        cleared = sum(axes_reset(username=user.email) for user in queryset)
        self.message_user(request, f"Cleared {cleared} lockout record(s).", messages.SUCCESS)

    @admin.action(description="End all sessions (log out everywhere)")
    def end_sessions(self, request, queryset):
        users = list(queryset)
        for user in users:
            end_all_sessions(user)
            log_event("logout_all", user=user)
        self.message_user(request, f"Ended all sessions for {len(users)} user(s).", messages.SUCCESS)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_default", "sort_order", "subscriber_count"]
    list_editable = ["sort_order"]
    prepopulated_fields = {"slug": ["name"]}
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Subscribers")
    def subscriber_count(self, obj):
        return obj.subscriptions.count()


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    """Read-only audit trail."""

    list_display = ["created_at", "event", "email", "ip", "user_agent_short"]
    list_filter = ["event", "created_at"]
    search_fields = ["email", "ip"]
    date_hierarchy = "created_at"

    @admin.display(description="User agent")
    def user_agent_short(self, obj):
        return (obj.user_agent[:60] + "…") if len(obj.user_agent) > 60 else obj.user_agent

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
