from django.contrib import admin

from .models import Portfolio


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "base_currency", "created_at"]
    list_filter = ["base_currency"]
    search_fields = ["name", "owner__email"]
    list_select_related = ["owner"]
    readonly_fields = ["owner", "base_currency", "created_at", "updated_at"]

    def has_add_permission(self, request):
        # Portfolios are created with their user (one each); base currency
        # follows the user's profile.
        return False
