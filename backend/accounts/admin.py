from axes.utils import reset as axes_reset
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .audit import log_event
from .emails import send_password_reset_email
from .forms import ProfileInlineForm, UserChangeForm, UserCreationForm
from .models import Profile, SecurityEvent, User
from .sessions import end_all_sessions

# Basic admin branding. Nowhere better to put this yet - accounts is the
# only app registered so far; move it to a `core` app if/when one exists.
admin.site.site_header = "Portfolio Dashboard admin"
admin.site.site_title = "Portfolio Dashboard admin"
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


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User
    inlines = [ProfileInline]

    list_display = [
        "email",
        "display_name_column",
        "role_column",
        "is_active",
        "is_staff",
        "email_verified_badge",
        "last_login",
        "date_joined",
    ]
    list_filter = ["is_active", "is_staff", "profile__role", EmailVerifiedFilter]
    search_fields = ["email", "profile__display_name"]
    ordering = ["email"]
    list_per_page = 50

    readonly_fields = [
        "last_login",
        "date_joined",
        "password_changed_at",
        "email_verified_at",
    ]

    fieldsets = (
        ("Account", {"fields": ("email", "password")}),
        (
            "Verification & security",
            {"fields": ("email_verified_at", "password_changed_at", "last_login", "date_joined")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )

    actions = [
        "deactivate_users",
        "reactivate_users",
        "mark_email_verified",
        "send_password_reset_email_action",
        "unlock_users",
        "end_sessions",
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("profile")

    def get_inline_instances(self, request, obj=None):
        # Profile is created automatically by the post_save signal once the
        # user exists (signals.py) - there's nothing to show an inline for
        # on the add page, and submitting one there would just race the
        # signal for the same OneToOne row.
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    @admin.display(description="Display name", ordering="profile__display_name")
    def display_name_column(self, obj):
        return obj.profile.display_name or "—"

    @admin.display(description="Role", ordering="profile__role")
    def role_column(self, obj):
        return obj.profile.get_role_display()

    @admin.display(description="Email verified", boolean=False)
    def email_verified_badge(self, obj):
        if obj.is_email_verified:
            return format_html('<span style="color:#1a7f37;font-weight:600;">&#10003; verified</span>')
        return format_html('<span style="color:#b42318;font-weight:600;">&#10007; unverified</span>')

    # Audit rows written by admin actions pass request=None: the request is
    # the *staff member's*, and recording their IP/user agent against the
    # target user's account would misattribute it.

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        # Matches the self-service deactivate/ endpoint: sessions end now,
        # rather than lingering until the next request notices is_active.
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

    @admin.action(description="End all sessions (log out everywhere)")
    def end_sessions(self, request, queryset):
        for user in queryset:
            end_all_sessions(user)
            log_event("logout_all", user=user)
        self.message_user(request, f"Ended all sessions for {queryset.count()} user(s).", messages.SUCCESS)

    @admin.action(description="Mark email verified")
    def mark_email_verified(self, request, queryset):
        from django.utils import timezone

        updated = queryset.filter(email_verified_at__isnull=True).update(
            email_verified_at=timezone.now()
        )
        self.message_user(request, f"Marked {updated} user(s) as verified.", messages.SUCCESS)

    @admin.action(description="Send password-reset email")
    def send_password_reset_email_action(self, request, queryset):
        count = 0
        for user in queryset:
            send_password_reset_email(user)
            count += 1
        self.message_user(request, f"Sent {count} password-reset email(s).", messages.SUCCESS)

    @admin.action(description="Unlock (clear lockout)")
    def unlock_users(self, request, queryset):
        cleared = sum(axes_reset(username=user.email) for user in queryset)
        self.message_user(
            request,
            f"Cleared {cleared} lockout record(s) across {queryset.count()} user(s).",
            messages.SUCCESS,
        )


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ["created_at", "event", "user_email_column", "ip", "user_agent_short"]
    list_filter = ["event", "created_at"]
    search_fields = ["user__email", "ip"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    @admin.display(description="User", ordering="user__email")
    def user_email_column(self, obj):
        return obj.user.email if obj.user_id else "—"

    @admin.display(description="User agent")
    def user_agent_short(self, obj):
        return (obj.user_agent[:60] + "…") if len(obj.user_agent) > 60 else obj.user_agent

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
