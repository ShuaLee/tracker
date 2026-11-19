"""me/, options/, logout-all/ and security-events/."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import SecurityEvent, User

from .helpers import AuthAPITestCase, make_user

ME = reverse("users:me")


class MeTests(AuthAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("me@example.com")
        self.client.force_login(self.user)

    def test_get(self):
        data = self.client.get(ME).data
        self.assertEqual(data["email"], "me@example.com")
        self.assertFalse(data["is_email_verified"])
        self.assertEqual(data["plan"], {"slug": "free", "name": "Free"})
        self.assertEqual(data["profile"], {"display_name": "", "base_currency": "CAD", "timezone": "America/Toronto"})
        self.assertNotIn("password", data)

    def test_requires_login(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.get(ME).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(anonymous.patch(ME, {}, format="json").status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_profile_partially(self):
        self.client.patch(ME, {"profile": {"base_currency": "EUR"}}, format="json")
        response = self.client.patch(ME, {"profile": {"display_name": "Me", "timezone": "Europe/London"}}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        profile = User.objects.get(pk=self.user.pk).profile
        self.assertEqual((profile.display_name, profile.base_currency, profile.timezone), ("Me", "EUR", "Europe/London"))

    def test_rejects_invalid_timezone_and_currency(self):
        for profile in ({"timezone": "Not/AZone"}, {"base_currency": "XYZ"}):
            response = self.client.patch(ME, {"profile": profile}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, profile)
            self.assertIn(next(iter(profile)), response.data["profile"])

    def test_email_plan_and_dates_are_read_only(self):
        response = self.client.patch(
            ME, {"email": "other@example.com", "plan": {"slug": "pro"}, "is_email_verified": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(user.email, "me@example.com")
        self.assertFalse(user.is_email_verified)
        self.assertEqual(response.data["plan"]["slug"], "free")


class OptionsTests(AuthAPITestCase):
    def test_public_and_lists_choices(self):
        response = APIClient().get(reverse("users:options"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn({"value": "CAD", "label": "Canadian dollar"}, response.data["currencies"])
        self.assertIn("America/Toronto", response.data["timezones"])
        self.assertEqual(response.data["timezones"], sorted(response.data["timezones"]))


class LogoutAllTests(AuthAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("multi@example.com")
        self.client.force_login(self.user)
        self.other_device = APIClient()
        self.other_device.force_login(self.user)
        self.bystander = APIClient()
        self.bystander.force_login(make_user("else@example.com"))

    def _signed_in(self, client):
        return client.get(ME).status_code == status.HTTP_200_OK

    def test_default_ends_every_session_including_this_one(self):
        self.assertEqual(self.client.post(reverse("users:logout-all"), {}, format="json").status_code, 200)
        self.assertFalse(self._signed_in(self.client))
        self.assertFalse(self._signed_in(self.other_device))
        self.assertTrue(self._signed_in(self.bystander))
        self.assertTrue(SecurityEvent.objects.filter(event="logout_all", user=self.user).exists())

    def test_keep_current_ends_only_the_others(self):
        self.client.post(reverse("users:logout-all"), {"keep_current": True}, format="json")
        self.assertTrue(self._signed_in(self.client))
        self.assertFalse(self._signed_in(self.other_device))
        self.assertTrue(self._signed_in(self.bystander))


class SecurityEventsTests(AuthAPITestCase):
    def test_lists_own_events_newest_first_capped(self):
        from users.views import SECURITY_EVENTS_LIMIT

        user = make_user("audit@example.com")
        other = make_user("other@example.com")
        SecurityEvent.objects.create(user=other, email=other.email, event="login", ip="10.0.0.2")
        SecurityEvent.objects.bulk_create(
            SecurityEvent(user=user, email=user.email, event="password_changed") for _ in range(SECURITY_EVENTS_LIMIT)
        )
        self.client.force_login(user)  # adds a newer "login" event

        data = self.client.get(reverse("users:security-events")).data
        self.assertEqual(len(data), SECURITY_EVENTS_LIMIT)
        self.assertEqual(data[0]["event"], "login")
        self.assertEqual(data[1]["event_label"], "Password changed")
        self.assertNotIn("10.0.0.2", [e["ip"] for e in data])

    def test_requires_login(self):
        self.assertEqual(APIClient().get(reverse("users:security-events")).status_code, status.HTTP_403_FORBIDDEN)
