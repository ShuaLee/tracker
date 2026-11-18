"""
What each tier allows - the single place feature gates read from (PLAN.md 1.3a).

Nothing is gated yet: no feature exists that needs a limit. When one does
(e.g. how many assets on Free, automatic price updates, CSV import), add its
key to *every* tier in TIER_LIMITS and check it with `limit()` / `allows()` -
never by comparing tier names in feature code, so tiers can be renamed,
added or re-priced without touching features.
"""

from .models import Subscription

Tier = Subscription.Tier

# tier -> {feature key: limit}. A limit is a bool (feature on/off), an int
# (a cap), or None (unlimited). Every tier must list every key.
TIER_LIMITS = {
    Tier.FREE: {},
    Tier.PAID: {},
}


def tier_for(user):
    """The user's tier; Free for anyone without a subscription row (e.g. an
    anonymous user) so callers never have to special-case it."""
    subscription = getattr(user, "subscription", None) if getattr(user, "is_authenticated", False) else None
    return subscription.tier if subscription is not None else Tier.FREE


def limit(user, key):
    """The user's limit for `key`. Raises KeyError for a key no tier defines -
    a typo in a gate should fail loudly, not silently allow everything."""
    return TIER_LIMITS[tier_for(user)][key]


def allows(user, key):
    """True if the user's tier has `key` switched on (or uncapped)."""
    value = limit(user, key)
    return value is None or bool(value)
