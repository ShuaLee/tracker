"""
What a user's plan allows - the one helper every limit check goes through
(PLAN.md 2.11). Feature code asks `entitlements(user).get("max_sheets")`; it
never compares plan names, so plans can be renamed, added or re-priced in
admin without touching features. Nothing is enforced yet (step 11).
"""

from .models import Plan, Subscription

DEFAULT_PLAN_SLUG = "free"


def default_plan():
    """The plan new users start on. Created on demand if missing (e.g. a test
    database flushed after the data migration that seeds it)."""
    plan = Plan.objects.filter(is_default=True).first()
    if plan is None:
        plan, _ = Plan.objects.get_or_create(
            slug=DEFAULT_PLAN_SLUG, defaults={"name": "Free", "is_default": True}
        )
    return plan


def plan_for(user):
    """The plan whose entitlements apply to `user` right now: their
    subscription's plan while it's active, otherwise the default plan."""
    subscription = getattr(user, "subscription", None) if getattr(user, "is_authenticated", False) else None
    if subscription is not None and subscription.status == Subscription.Status.ACTIVE:
        return subscription.plan
    return default_plan()


def entitlements(user):
    """A copy of the limits and feature flags for `user`'s plan."""
    return dict(plan_for(user).entitlements)
