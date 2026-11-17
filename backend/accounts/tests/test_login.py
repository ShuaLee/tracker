from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import SecurityEvent, User

from .helpers import STRONG_PASSWORD


class LoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.login_url = reverse("auth-login")
        self.me_url = reverse("auth-me")
        self.user = User.objects.create_user(email="login@example.com", password=STRONG_PASSWORD)

    def test_login_success_returns_me_payload(self):
        response = self.client.post(
            self.login_url, {"email": self.user.email, "password": STRONG_PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)

        me_response = self.client.get(self.me_url)
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertTrue(SecurityEvent.objects.filter(event="login", user=self.user).exists())

    def test_login_wrong_password_generic_error(self):
        response = self.client.post(
            self.login_url, {"email": self.user.email, "password": "nope"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(SecurityEvent.objects.filter(event="login_failed", user=self.user).exists())

    def test_login_nonexistent_email_same_error_as_wrong_password(self):
        wrong_password_response = self.client.post(
            self.login_url, {"email": self.user.email, "password": "nope"}, format="json"
        )
        nonexistent_response = self.client.post(
            self.login_url, {"email": "nobody@example.com", "password": "nope"}, format="json"
        )
        self.assertEqual(nonexistent_response.status_code, wrong_password_response.status_code)
        self.assertEqual(nonexistent_response.data, wrong_password_response.data)

    def test_inactive_user_cannot_log_in_and_gets_the_same_generic_error(self):
        self.user.is_active = False
        self.user.save()

        response = self.client.post(
            self.login_url, {"email": self.user.email, "password": STRONG_PASSWORD}, format="json"
        )
        wrong_password_response = self.client.post(
            self.login_url, {"email": "login@example.com", "password": "nope"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, wrong_password_response.data)

    def test_unverified_user_can_still_log_in(self):
        self.assertFalse(self.user.is_email_verified)
        response = self.client.post(
            self.login_url, {"email": self.user.email, "password": STRONG_PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_ends_session(self):
        self.client.post(
            self.login_url, {"email": self.user.email, "password": STRONG_PASSWORD}, format="json"
        )
        self.client.post(reverse("auth-logout"))
        response = self.client.get(self.me_url)
        # 403, not 401: SessionAuthentication has no WWW-Authenticate header,
        # so DRF coerces NotAuthenticated to 403 (rest_framework.views.APIView.handle_exception).
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
