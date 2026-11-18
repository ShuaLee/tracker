from django.contrib import admin

from .models import Portfolio, PortfolioAccess
from .services import add_owner_access


class PortfolioAccessInline(admin.TabularInline):
    """Read-only for now: the only rows are owner rows, which must stay in step
    with Portfolio.owner. Granting/revoking access arrives with sharing (B9),
    through services that enforce the rules - not through a raw inline."""

    model = PortfolioAccess
    fk_name = "portfolio"
    extra = 0
    can_delete = False
    fields = ["user", "role", "status", "granted_by", "created_at", "revoked_at"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "base_currency", "access_count", "created_at"]
    list_filter = ["base_currency", "created_at"]
    search_fields = ["name", "owner__email", "owner__profile__display_name"]
    list_select_related = ["owner"]
    autocomplete_fields = ["owner"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [PortfolioAccessInline]

    def get_readonly_fields(self, request, obj=None):
        # Owner is chosen on create only. Changing it later would desync the
        # owner access row; ownership transfer would be a future service.
        if obj is not None:
            return ["owner", *self.readonly_fields]
        return self.readonly_fields

    def get_inline_instances(self, request, obj=None):
        # Nothing to show until the portfolio (and its owner row) exist.
        return [] if obj is None else super().get_inline_instances(request, obj)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            # Same transaction (admin's changeform view is atomic).
            add_owner_access(obj)

    @admin.display(description="People with access")
    def access_count(self, obj):
        return obj.access.filter(status=PortfolioAccess.Status.ACTIVE).count()


@admin.register(PortfolioAccess)
class PortfolioAccessAdmin(admin.ModelAdmin):
    """Read-only audit view of every access row, filterable by role/status."""

    list_display = ["portfolio", "user", "role", "status", "granted_by", "created_at", "revoked_at"]
    list_filter = ["role", "status"]
    search_fields = ["portfolio__name", "user__email"]
    list_select_related = ["portfolio", "user", "granted_by"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
