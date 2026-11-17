"""
DRF's cache-backed throttles persist across requests within one test process
(the default cache is LocMemCache), so every test here clears the cache in
setUp - otherwise an earlier test's counter would bleed into this one.
"""

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .helpers import STRONG_PASSWORD


class ThrottlingTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_register_is_throttled_per_ip(self):
        url = reverse("auth-register")
        # DEFAULT_THROTTLE_RATES["register"] = "5/min" (config/settings/base.py)
        for _ in range(5):
            response = self.client.post(
                url, {"email": "same@example.com", "password": STRONG_PASSWORD}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        sixth = self.client.post(
            url, {"email": "same@example.com", "password": STRONG_PASSWORD}, format="json"
        )
        self.assertEqual(sixth.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_login_is_throttled_per_ip(self):
        User.objects.create_user(email="throttle@example.com", password=STRONG_PASSWORD)
        url = reverse("auth-login")
        # DEFAULT_THROTTLE_RATES["login"] = "5/min"
        for _ in range(5):
            response = self.client.post(
                url, {"email": "throttle@example.com", "password": "wrong"}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        sixth = self.client.post(
            url, {"email": "throttle@example.com", "password": "wrong"}, format="json"
        )
        self.assertEqual(sixth.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
