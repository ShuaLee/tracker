from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import SecurityEvent, User

from .helpers import STRONG_PASSWORD


class LogoutAllTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("auth-logout-all")
        self.user = User.objects.create_user(email="multi@example.com", password=STRONG_PASSWORD)
        # Two independent sessions for the same user ("laptop" and "phone"),
        # plus someone else's that must survive.
        self.client.force_login(self.user)
        self.other_device = APIClient()
        self.other_device.force_login(self.user)
        self.bystander = APIClient()
        self.bystander.force_login(User.objects.create_user(email="else@example.com", password=STRONG_PASSWORD))

    def _logged_in(self, client):
        return client.get(reverse("auth-me")).status_code == status.HTTP_200_OK

    def test_default_ends_every_session_including_this_one(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self._logged_in(self.client))
        self.assertFalse(self._logged_in(self.other_device))
        self.assertTrue(self._logged_in(self.bystander))
        self.assertTrue(SecurityEvent.objects.filter(event="logout_all", user=self.user).exists())

    def test_keep_current_ends_only_the_others(self):
        response = self.client.post(self.url, {"keep_current": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self._logged_in(self.client))
        self.assertFalse(self._logged_in(self.other_device))
        self.assertTrue(self._logged_in(self.bystander))

    def test_requires_login(self):
        self.assertEqual(APIClient().post(self.url, {}, format="json").status_code, status.HTTP_403_FORBIDDEN)


class SecurityEventsTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("auth-security-events")
        self.user = User.objects.create_user(email="audit@example.com", password=STRONG_PASSWORD)
        self.other = User.objects.create_user(email="other@example.com", password=STRONG_PASSWORD)

    def test_lists_only_own_events_newest_first(self):
        SecurityEvent.objects.create(user=self.user, event="password_changed", ip="10.0.0.1")
        SecurityEvent.objects.create(user=self.other, event="login", ip="10.0.0.2")
        self.client.force_login(self.user)  # writes this user's "login" event

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([e["event"] for e in response.data], ["login", "password_changed"])
        self.assertEqual(response.data[1]["event_label"], "Password changed")
        self.assertEqual(response.data[1]["ip"], "10.0.0.1")
        self.assertNotIn("10.0.0.2", [e["ip"] for e in response.data])

    def test_includes_failed_logins_against_this_account(self):
        self.client.post(
            reverse("auth-login"), {"email": self.user.email, "password": "wrong"}, format="json"
        )
        self.client.force_login(self.user)
        events = [e["event"] for e in self.client.get(self.url).data]
        self.assertIn("login_failed", events)

    def test_capped_at_limit(self):
        from accounts.views import SECURITY_EVENTS_LIMIT

        SecurityEvent.objects.bulk_create(
            SecurityEvent(user=self.user, event="login") for _ in range(SECURITY_EVENTS_LIMIT + 10)
        )
        self.client.force_login(self.user)
        self.assertEqual(len(self.client.get(self.url).data), SECURITY_EVENTS_LIMIT)

    def test_requires_login(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)
