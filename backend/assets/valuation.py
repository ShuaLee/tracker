"""
Value, cost and gain - of one holding and of a whole portfolio, in its base
currency (PLAN.md 2.2, step 2). Plain functions over plain inputs, so they're
easy to test; only `portfolio_totals()` touches the database.

Rules ("numbers you can trust", PRODUCT.md):
- value = quantity × current_price; cost basis = quantity × avg_cost;
  unrealized gain = value − cost basis, only when both exist.
- A holding with no current price is **unpriced**: left out of every total
  and listed, never counted as zero.
- A holding whose currency can't be converted (no exchange rate) is left out
  and its currency listed in `missing_rates`, never converted 1:1.
- Totals are full-precision Decimals; round only for display (`money()`).
"""

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0")
CENT = Decimal("0.01")


def money(amount):
    """Round to cents for display. None stays None."""
    return None if amount is None else amount.quantize(CENT, rounding=ROUND_HALF_UP)


# --- one holding, in its own currency ----------------------------------------


def holding_value(holding):
    if holding.current_price is None:
        return None
    return holding.quantity * holding.current_price


def holding_cost(holding):
    if holding.avg_cost is None:
        return None
    return holding.quantity * holding.avg_cost


def holding_gain(holding):
    value, cost = holding_value(holding), holding_cost(holding)
    if value is None or cost is None:
        return None
    return value - cost


# --- currency conversion ------------------------------------------------------


class Rates:
    """Exchange-rate lookup from (from_currency, to_currency) -> rate, where
    1 from_currency = rate to_currency. The inverse pair is derived."""

    def __init__(self, pairs=None):
        self._pairs = dict(pairs or {})

    @classmethod
    def for_portfolio(cls, portfolio):
        return cls(
            ((rate.from_currency, rate.to_currency), rate.rate) for rate in portfolio.exchange_rates.all()
        )

    def convert(self, amount, from_currency, to_currency):
        """`amount` in to_currency, or None if no rate (direct or inverse)."""
        if from_currency == to_currency:
            return amount
        if (from_currency, to_currency) in self._pairs:
            return amount * self._pairs[(from_currency, to_currency)]
        if (to_currency, from_currency) in self._pairs:
            return amount / self._pairs[(to_currency, from_currency)]
        return None


# --- many holdings, in a base currency ---------------------------------------


@dataclass
class Totals:
    currency: str
    net_worth: Decimal = ZERO  # investments + personal
    investments: Decimal = ZERO
    personal: Decimal = ZERO
    # Over holdings that have an avg_cost (and could be converted).
    cost_basis: Decimal = ZERO
    # Over holdings that have both a price and an avg_cost.
    unrealized_gain: Decimal = ZERO
    holding_count: int = 0
    unpriced: list = field(default_factory=list)  # holdings with no current price
    missing_rates: set = field(default_factory=set)  # currencies with no rate to `currency`

    @property
    def is_complete(self):
        """True when every holding made it into the totals."""
        return not self.unpriced and not self.missing_rates


def totals(holdings, base_currency, rates):
    """Net worth, investments, personal, cost basis and unrealized gain of
    `holdings`, in `base_currency`."""
    result = Totals(currency=base_currency)
    for holding in holdings:
        result.holding_count += 1
        value = holding_value(holding)
        if value is None:
            result.unpriced.append(holding)
            continue
        value = rates.convert(value, holding.currency, base_currency)
        if value is None:
            result.missing_rates.add(holding.currency)
            continue

        result.net_worth += value
        if holding.is_investment:
            result.investments += value
        else:
            result.personal += value

        cost = holding_cost(holding)
        if cost is not None:
            cost = rates.convert(cost, holding.currency, base_currency)  # same rate as value: never None here
            result.cost_basis += cost
            result.unrealized_gain += value - cost
    return result


def value_by(holdings, base_currency, rates, key):
    """Converted value of `holdings` grouped by `key(holding)` (e.g. asset
    type name, account name), largest first. Holdings that are unpriced or
    can't be converted are skipped, as in `totals()`."""
    groups = defaultdict(lambda: ZERO)
    for holding in holdings:
        value = holding_value(holding)
        if value is None:
            continue
        value = rates.convert(value, holding.currency, base_currency)
        if value is not None:
            groups[key(holding)] += value
    return dict(sorted(groups.items(), key=lambda item: item[1], reverse=True))


def portfolio_holdings(portfolio):
    return portfolio.holdings.select_related("asset_type", "account")


def portfolio_totals(portfolio):
    """`totals()` for one portfolio, using its own holdings and rates."""
    return totals(portfolio_holdings(portfolio), portfolio.base_currency, Rates.for_portfolio(portfolio))
