from django.contrib import admin

from .models import Portfolio


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "base_currency", "created_at"]
    list_filter = ["base_currency", "created_at"]
    search_fields = ["name", "owner__email", "owner__profile__display_name"]
    list_select_related = ["owner"]
    autocomplete_fields = ["owner"]
    readonly_fields = ["created_at", "updated_at"]

    def get_readonly_fields(self, request, obj=None):
        # Owner is chosen on create only: reassigning would leave the old
        # owner with no portfolio and the new one with two.
        if obj is not None:
            return ["owner", *self.readonly_fields]
        return self.readonly_fields
