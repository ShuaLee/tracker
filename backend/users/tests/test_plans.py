from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.test import TestCase

from users.entitlements import default_plan, entitlements, plan_for
from users.models import Plan, Subscription

from .helpers import make_user


class PlanTests(TestCase):
    def test_free_plan_is_seeded_as_the_default(self):
        free = Plan.objects.get(slug="free")
        self.assertTrue(free.is_default)
        self.assertEqual(default_plan(), free)

    def test_only_one_default_plan(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Plan.objects.create(slug="pro", name="Pro", is_default=True)

    def test_default_plan_is_recreated_if_missing(self):
        Subscription.objects.all().delete()
        Plan.objects.all().delete()
        self.assertEqual(default_plan().slug, "free")


class EntitlementsTests(TestCase):
    def setUp(self):
        self.free = Plan.objects.get(slug="free")
        self.free.entitlements = {"max_sheets": 3, "live_prices": False}
        self.free.save()
        self.pro = Plan.objects.create(slug="pro", name="Pro", entitlements={"max_sheets": None, "live_prices": True})
        self.user = make_user()

    def test_new_user_gets_free_entitlements(self):
        self.assertEqual(plan_for(self.user), self.free)
        self.assertEqual(entitlements(self.user), {"max_sheets": 3, "live_prices": False})

    def test_active_paid_subscription_gets_its_plan(self):
        self.user.subscription.plan = self.pro
        self.user.subscription.save()
        self.assertTrue(entitlements(self.user)["live_prices"])

    def test_inactive_subscription_falls_back_to_default(self):
        self.user.subscription.plan = self.pro
        self.user.subscription.status = Subscription.Status.PAST_DUE
        self.user.subscription.save()
        self.assertEqual(plan_for(self.user), self.free)

    def test_anonymous_gets_default(self):
        self.assertEqual(plan_for(AnonymousUser()), self.free)

    def test_returns_a_copy(self):
        entitlements(self.user)["max_sheets"] = 999
        self.free.refresh_from_db()
        self.assertEqual(self.free.entitlements["max_sheets"], 3)
