from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts import tiers
from accounts.models import Subscription, User

from .helpers import STRONG_PASSWORD


class SubscriptionTests(TestCase):
    def test_new_user_starts_on_free(self):
        user = User.objects.create_user(email="new@example.com", password=STRONG_PASSWORD)
        self.assertEqual(user.subscription.tier, Subscription.Tier.FREE)
        self.assertEqual(tiers.tier_for(user), "free")

    def test_tier_for_anonymous_or_missing_row_is_free(self):
        self.assertEqual(tiers.tier_for(AnonymousUser()), "free")
        user = User.objects.create_user(email="norow@example.com", password=STRONG_PASSWORD)
        user.subscription.delete()
        user = User.objects.get(pk=user.pk)
        self.assertEqual(tiers.tier_for(user), "free")

    def test_every_tier_defines_the_same_limit_keys(self):
        # A gate added to one tier but forgotten in another would KeyError
        # for those users - catch it here instead.
        self.assertEqual(set(tiers.TIER_LIMITS), set(Subscription.Tier.values))
        key_sets = {tier: set(limits) for tier, limits in tiers.TIER_LIMITS.items()}
        self.assertEqual(len(set(map(frozenset, key_sets.values()))), 1, key_sets)

    def test_limit_and_allows(self):
        user = User.objects.create_user(email="gate@example.com", password=STRONG_PASSWORD)
        fake = {"free": {"max_assets": 25, "csv_import": False}, "paid": {"max_assets": None, "csv_import": True}}
        original = tiers.TIER_LIMITS
        tiers.TIER_LIMITS = fake
        try:
            self.assertEqual(tiers.limit(user, "max_assets"), 25)
            self.assertFalse(tiers.allows(user, "csv_import"))
            user.subscription.tier = "paid"
            user.subscription.save()
            self.assertIsNone(tiers.limit(user, "max_assets"))
            self.assertTrue(tiers.allows(user, "csv_import"))
            with self.assertRaises(KeyError):
                tiers.limit(user, "typo_key")
        finally:
            tiers.TIER_LIMITS = original


class TierInMeTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="me@example.com", password=STRONG_PASSWORD)
        self.client.force_login(self.user)

    def test_me_shows_tier(self):
        self.assertEqual(self.client.get(reverse("auth-me")).data["tier"], "free")
        self.user.subscription.tier = "paid"
        self.user.subscription.save()
        self.assertEqual(self.client.get(reverse("auth-me")).data["tier"], "paid")

    def test_tier_cannot_be_self_assigned(self):
        response = self.client.patch(reverse("auth-me"), {"tier": "paid"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["tier"], "free")
        self.assertEqual(Subscription.objects.get(user=self.user).tier, "free")


class TierAdminTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password=STRONG_PASSWORD))
        self.target = User.objects.create_user(email="target@example.com", password=STRONG_PASSWORD)

    def test_set_tier_actions(self):
        changelist = reverse("admin:accounts_user_changelist")
        self.client.post(changelist, {"action": "set_tier_paid", "_selected_action": [self.target.pk]})
        self.assertEqual(Subscription.objects.get(user=self.target).tier, "paid")
        self.client.post(changelist, {"action": "set_tier_free", "_selected_action": [self.target.pk]})
        self.assertEqual(Subscription.objects.get(user=self.target).tier, "free")

    def test_changelist_filter_and_change_page_render(self):
        changelist = self.client.get(reverse("admin:accounts_user_changelist"), {"subscription__tier": "free"})
        self.assertContains(changelist, "target@example.com")
        change = self.client.get(reverse("admin:accounts_user_change", args=[self.target.pk]))
        self.assertEqual(change.status_code, 200)
        self.assertContains(change, 'name="subscription-0-tier"')
