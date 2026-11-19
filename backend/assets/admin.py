from django.contrib import admin
from django.utils.html import format_html, format_html_join

from . import valuation
from .forms import HoldingAdminForm
from .models import AssetField, AssetType, Holding, PortfolioSummary


class StandardOrCustomFilter(admin.SimpleListFilter):
    title = "source"
    parameter_name = "source"

    def lookups(self, request, model_admin):
        return [("standard", "Standard"), ("custom", "User-made")]

    def queryset(self, request, queryset):
        if self.value() == "standard":
            return queryset.filter(portfolio__isnull=True)
        if self.value() == "custom":
            return queryset.filter(portfolio__isnull=False)
        return queryset


@admin.register(AssetType)
class AssetTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "owner_column", "is_investment", "is_priced", "key", "sort_order"]
    list_filter = [StandardOrCustomFilter, "is_investment", "is_priced"]
    search_fields = ["name", "key", "portfolio__owner__email"]
    list_select_related = ["portfolio__owner"]
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Owner", ordering="portfolio__owner__email")
    def owner_column(self, obj):
        return "Standard" if obj.is_standard else obj.portfolio.owner.email


@admin.register(AssetField)
class AssetFieldAdmin(admin.ModelAdmin):
    list_display = ["name", "asset_type", "field_type", "key", "portfolio"]
    list_filter = ["field_type"]
    search_fields = ["name", "key", "portfolio__owner__email"]
    list_select_related = ["asset_type__portfolio__owner", "portfolio__owner"]
    readonly_fields = ["key"]


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    form = HoldingAdminForm
    list_display = [
        "name",
        "symbol",
        "asset_type",
        "account",
        "quantity",
        "current_price",
        "currency",
        "value_column",
        "gain_column",
        "is_investment_column",
        "owner_column",
    ]
    list_filter = ["asset_type", "currency", "investment_override", "account__kind"]
    search_fields = ["name", "symbol", "portfolio__owner__email"]
    list_select_related = ["asset_type__portfolio__owner", "account__portfolio__owner", "portfolio__owner"]
    readonly_fields = ["price_updated_at", "created_at", "updated_at", "value_summary"]

    BASE_FIELDSETS = [
        (None, {"fields": ["portfolio", "asset_type", "account", "name", "symbol"]}),
        ("Position", {"fields": ["quantity", "avg_cost", "current_price", "currency", "price_updated_at"]}),
        ("Classification", {"fields": ["investment_override"]}),
    ]

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(self.BASE_FIELDSETS)
        if obj is None:
            fieldsets.append(
                ("Custom fields", {"fields": [], "description": "Save the holding first; its asset type's custom fields then appear here."})
            )
        else:
            # Custom inputs are added per holding by HoldingAdminForm.
            custom = [f"custom__{f.key}" for f in obj.available_fields()]
            if custom:
                fieldsets.append(("Custom fields", {"fields": custom}))
        fieldsets.append(("Notes", {"fields": ["notes"]}))
        if obj is not None:
            fieldsets.append(("Calculated", {"fields": ["value_summary", "created_at", "updated_at"]}))
        return fieldsets

    def get_form(self, request, obj=None, change=False, **kwargs):
        # The admin builds the form class from the fieldsets' names, and the
        # per-holding custom__ inputs aren't model fields - leave them out
        # here; HoldingAdminForm.__init__ adds them to each form instance.
        names = [name for _, opts in self.get_fieldsets(request, obj) for name in opts["fields"]]
        kwargs["fields"] = [name for name in names if not name.startswith("custom__")]
        return super().get_form(request, obj, change=change, **kwargs)

    @admin.display(description="Value")
    def value_column(self, obj):
        return valuation.money(valuation.holding_value(obj))

    @admin.display(description="Gain")
    def gain_column(self, obj):
        return valuation.money(valuation.holding_gain(obj))

    @admin.display(description="Investment", boolean=True)
    def is_investment_column(self, obj):
        return obj.is_investment

    @admin.display(description="Owner", ordering="portfolio__owner__email")
    def owner_column(self, obj):
        return obj.portfolio.owner.email

    @admin.display(description="Value, cost and gain")
    def value_summary(self, obj):
        rows = [
            ("Value", valuation.money(valuation.holding_value(obj))),
            ("Cost basis", valuation.money(valuation.holding_cost(obj))),
            ("Unrealized gain", valuation.money(valuation.holding_gain(obj))),
        ]
        return format_html(
            "<table>{}</table><p>In {}. Blank = not enough data (no price or no average cost).</p>",
            format_html_join("", "<tr><th>{}</th><td>{}</td></tr>", ((label, "—" if v is None else v) for label, v in rows)),
            obj.currency,
        )


@admin.register(PortfolioSummary)
class PortfolioSummaryAdmin(admin.ModelAdmin):
    """Read-only totals per portfolio: the "done when" of PLAN.md step 2 made
    visible - net worth, investments, personal, cost and gain, plus anything
    left out (unpriced holdings, missing exchange rates)."""

    list_display = ["owner", "base_currency", "net_worth", "investments", "personal", "unrealized_gain", "warnings"]
    list_select_related = ["owner"]
    search_fields = ["owner__email"]
    fields = ["owner", "base_currency", "totals_table", "by_asset_type", "by_account", "left_out"]
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # read-only page; view permission is enough

    def _totals(self, obj):
        # Cached per object so the list's several columns compute once.
        if not hasattr(obj, "_totals"):
            obj._totals = valuation.portfolio_totals(obj)
        return obj._totals

    @admin.display(description="Net worth")
    def net_worth(self, obj):
        return valuation.money(self._totals(obj).net_worth)

    @admin.display(description="Investments")
    def investments(self, obj):
        return valuation.money(self._totals(obj).investments)

    @admin.display(description="Personal")
    def personal(self, obj):
        return valuation.money(self._totals(obj).personal)

    @admin.display(description="Unrealized gain")
    def unrealized_gain(self, obj):
        return valuation.money(self._totals(obj).unrealized_gain)

    @admin.display(description="Left out")
    def warnings(self, obj):
        t = self._totals(obj)
        parts = []
        if t.unpriced:
            parts.append(f"{len(t.unpriced)} unpriced")
        if t.missing_rates:
            parts.append(f"no rate for {', '.join(sorted(t.missing_rates))}")
        return "; ".join(parts) or "—"

    @admin.display(description="Totals")
    def totals_table(self, obj):
        t = self._totals(obj)
        rows = [
            ("Net worth", t.net_worth),
            ("Investments", t.investments),
            ("Personal", t.personal),
            ("Cost basis", t.cost_basis),
            ("Unrealized gain", t.unrealized_gain),
        ]
        return format_html(
            "<table>{}</table><p>{} holdings, in {}.</p>",
            format_html_join("", "<tr><th>{}</th><td>{}</td></tr>", ((label, valuation.money(v)) for label, v in rows)),
            t.holding_count,
            t.currency,
        )

    def _breakdown(self, obj, key):
        values = valuation.value_by(
            valuation.portfolio_holdings(obj), obj.base_currency, valuation.Rates.for_portfolio(obj), key
        )
        if not values:
            return "—"
        return format_html(
            "<table>{}</table>",
            format_html_join("", "<tr><th>{}</th><td>{}</td></tr>", ((k, valuation.money(v)) for k, v in values.items())),
        )

    @admin.display(description="By asset type")
    def by_asset_type(self, obj):
        return self._breakdown(obj, lambda h: h.asset_type.name)

    @admin.display(description="By account")
    def by_account(self, obj):
        return self._breakdown(obj, lambda h: h.account.name if h.account else "(no account)")

    @admin.display(description="Left out of the totals")
    def left_out(self, obj):
        t = self._totals(obj)
        if t.is_complete:
            return "Nothing - every holding is included."
        items = [f"No current price: {h}" for h in t.unpriced]
        items += [f"No exchange rate from {c} to {t.currency} (add one on the portfolio)" for c in sorted(t.missing_rates)]
        return format_html("<ul>{}</ul>", format_html_join("", "<li>{}</li>", ((item,) for item in items)))
