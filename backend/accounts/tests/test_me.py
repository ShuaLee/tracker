from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .helpers import STRONG_PASSWORD


class MeTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("auth-me")
        self.user = User.objects.create_user(email="me@example.com", password=STRONG_PASSWORD)
        self.client.force_login(self.user)

    def test_get_returns_user_and_profile(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "me@example.com")
        self.assertFalse(response.data["is_email_verified"])
        self.assertIn("date_joined", response.data)
        self.assertEqual(
            response.data["profile"],
            {
                "display_name": "",
                "base_currency": "CAD",
                "timezone": "America/Toronto",
                "role": "individual",
            },
        )
        # Never leak secrets or internals.
        self.assertNotIn("password", response.data)

    def test_requires_login(self):
        self.client.logout()
        # 403, not 401 - see the comment in test_login.py's test_logout_ends_session.
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.patch(self.url, {"profile": {"display_name": "x"}}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_patch_updates_profile_fields(self):
        response = self.client.patch(
            self.url,
            {"profile": {"display_name": "Me", "base_currency": "USD", "timezone": "Europe/London"}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["profile"]["display_name"], "Me")

        profile = User.objects.get(pk=self.user.pk).profile
        self.assertEqual(
            (profile.display_name, profile.base_currency, profile.timezone),
            ("Me", "USD", "Europe/London"),
        )

    def test_partial_patch_leaves_other_fields_alone(self):
        self.client.patch(self.url, {"profile": {"base_currency": "EUR"}}, format="json")
        self.client.patch(self.url, {"profile": {"display_name": "Only name"}}, format="json")
        profile = User.objects.get(pk=self.user.pk).profile
        self.assertEqual(profile.base_currency, "EUR")
        self.assertEqual(profile.display_name, "Only name")

    def test_rejects_invalid_timezone(self):
        response = self.client.patch(self.url, {"profile": {"timezone": "Not/AZone"}}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("timezone", response.data["profile"])
        self.assertEqual(User.objects.get(pk=self.user.pk).profile.timezone, "America/Toronto")

    def test_rejects_invalid_currency(self):
        response = self.client.patch(self.url, {"profile": {"base_currency": "XYZ"}}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("base_currency", response.data["profile"])

    def test_role_cannot_be_self_assigned(self):
        response = self.client.patch(self.url, {"profile": {"role": "advisor"}}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["profile"]["role"], "individual")
        self.assertEqual(User.objects.get(pk=self.user.pk).profile.role, "individual")

    def test_email_cannot_be_changed_here(self):
        response = self.client.patch(self.url, {"email": "other@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(User.objects.get(pk=self.user.pk).email, "me@example.com")


class OptionsTests(APITestCase):
    def test_public_and_lists_profile_choices(self):
        response = self.client.get(reverse("auth-options"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn({"value": "CAD", "label": "Canadian dollar"}, response.data["currencies"])
        self.assertEqual([r["value"] for r in response.data["roles"]], ["individual", "advisor"])
        self.assertIn("America/Toronto", response.data["timezones"])
        self.assertEqual(response.data["timezones"], sorted(response.data["timezones"]))
