from django.contrib import admin

from .models import Account, ExchangeRate, Portfolio


class AccountInline(admin.TabularInline):
    model = Account
    extra = 0
    fields = ["name", "kind", "institution", "sort_order"]


class ExchangeRateInline(admin.TabularInline):
    model = ExchangeRate
    extra = 0
    fields = ["from_currency", "to_currency", "rate", "updated_at"]
    readonly_fields = ["updated_at"]


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "base_currency", "created_at"]
    list_filter = ["base_currency"]
    search_fields = ["name", "owner__email"]
    list_select_related = ["owner"]
    readonly_fields = ["owner", "base_currency", "created_at", "updated_at"]
    inlines = [AccountInline, ExchangeRateInline]

    def has_add_permission(self, request):
        # Portfolios are created with their user (one each); base currency
        # follows the user's profile.
        return False


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "institution", "portfolio"]
    list_filter = ["kind"]
    search_fields = ["name", "institution", "portfolio__owner__email"]
    list_select_related = ["portfolio__owner"]


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ["__str__", "portfolio", "updated_at"]
    list_filter = ["from_currency", "to_currency"]
    search_fields = ["portfolio__owner__email"]
    list_select_related = ["portfolio__owner"]
