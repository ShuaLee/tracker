from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import SecurityEvent, User

from .helpers import STRONG_PASSWORD


@override_settings(AXES_FAILURE_LIMIT=3)
class LockoutTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="lockout@example.com", password=STRONG_PASSWORD)
        self.url = reverse("auth-login")

    def test_repeated_bad_logins_lock_out_even_the_right_password(self):
        for _ in range(3):
            response = self.client.post(
                self.url, {"email": self.user.email, "password": "wrong"}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Correct password, but the (account, IP) combination is now locked
        # out - same generic error as a wrong password, so lockout state
        # isn't observable from outside.
        response = self.client.post(
            self.url, {"email": self.user.email, "password": STRONG_PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(SecurityEvent.objects.filter(event="locked", user=self.user).exists())
