from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from users.models import SecurityEvent

from .helpers import STRONG_PASSWORD, AuthAPITestCase, make_user

LOGIN = reverse("users:login")
ME = reverse("users:me")


class LoginTests(AuthAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("login@example.com")

    def test_success_returns_me_payload_and_starts_session(self):
        response = self.login(self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "login@example.com")
        self.assertEqual(self.client.get(ME).status_code, status.HTTP_200_OK)
        self.assertTrue(SecurityEvent.objects.filter(event="login", user=self.user).exists())

    def test_email_is_case_insensitive(self):
        response = self.client.post(LOGIN, {"email": "LOGIN@Example.com", "password": STRONG_PASSWORD}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_wrong_password_unknown_email_and_inactive_all_look_the_same(self):
        wrong = self.login(self.user, password="nope")
        unknown = self.client.post(LOGIN, {"email": "nobody@example.com", "password": "nope"}, format="json")
        self.user.is_active = False
        self.user.save()
        inactive = self.login(self.user)
        for response in (wrong, unknown, inactive):
            self.assertEqual((response.status_code, response.data), (wrong.status_code, wrong.data))
        self.assertEqual(wrong.status_code, status.HTTP_400_BAD_REQUEST)

    def test_failed_logins_are_logged_even_for_unknown_emails(self):
        self.login(self.user, password="nope")
        self.client.post(LOGIN, {"email": "nobody@example.com", "password": "nope"}, format="json")
        self.assertTrue(SecurityEvent.objects.filter(event="login_failed", user=self.user).exists())
        self.assertTrue(SecurityEvent.objects.filter(event="login_failed", user=None, email="nobody@example.com").exists())

    def test_unverified_user_can_log_in(self):
        self.assertFalse(self.user.is_email_verified)
        self.assertEqual(self.login(self.user).status_code, status.HTTP_200_OK)

    def test_login_rotates_the_session_key(self):
        self.client.get(reverse("users:csrf"))
        self.client.session.save()
        before = self.client.session.session_key
        self.login(self.user)
        self.assertNotEqual(self.client.session.session_key, before)

    def test_logout_ends_session(self):
        self.login(self.user)
        self.client.post(reverse("users:logout"))
        self.assertEqual(self.client.get(ME).status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(SecurityEvent.objects.filter(event="logout", user=self.user).exists())


@override_settings(AXES_FAILURE_LIMIT=3)
class LockoutTests(AuthAPITestCase):
    def test_repeated_bad_logins_lock_out_even_the_right_password(self):
        user = make_user("lockout@example.com")
        for _ in range(3):
            self.assertEqual(self.login(user, password="wrong").status_code, status.HTTP_400_BAD_REQUEST)
        # Right password, but this (email, IP) is locked - and the error is
        # the generic one, so lockout isn't observable from outside.
        response = self.login(user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(SecurityEvent.objects.filter(event="locked", user=user).exists())


class ThrottleTests(AuthAPITestCase):
    def test_login_is_throttled_per_ip(self):
        user = make_user("throttle@example.com")
        for _ in range(5):  # "login": "5/min"
            self.assertEqual(self.login(user, password="wrong").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.login(user, password="wrong").status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_register_is_throttled_per_ip(self):
        url = reverse("users:register")
        body = {"email": "same@example.com", "password": STRONG_PASSWORD}
        for _ in range(5):  # "register": "5/min"
            self.assertEqual(self.client.post(url, body, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(url, body, format="json").status_code, status.HTTP_429_TOO_MANY_REQUESTS)
