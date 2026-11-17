from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import SecurityEvent, User

from .helpers import STRONG_PASSWORD


class DeactivateTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="bye@example.com", password=STRONG_PASSWORD)
        self.url = reverse("auth-deactivate")
        self.client.post(
            reverse("auth-login"), {"email": self.user.email, "password": STRONG_PASSWORD}, format="json"
        )

    def test_requires_correct_password(self):
        response = self.client.post(self.url, {"current_password": "wrong"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_success_deactivates_logs_out_and_blocks_further_login(self):
        response = self.client.post(
            self.url, {"current_password": STRONG_PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertTrue(SecurityEvent.objects.filter(event="deactivated", user=self.user).exists())

        # Current session ended.
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_403_FORBIDDEN)

        # Inactive users are refused at login.
        login_response = self.client.post(
            reverse("auth-login"), {"email": self.user.email, "password": STRONG_PASSWORD}, format="json"
        )
        self.assertEqual(login_response.status_code, status.HTTP_400_BAD_REQUEST)
