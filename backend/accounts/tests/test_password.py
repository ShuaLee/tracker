from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import SecurityEvent, User

from .helpers import STRONG_PASSWORD, extract_link, extract_query

NEW_PASSWORD = "4n0ther$trongOne99"


class ChangePasswordTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="change@example.com", password=STRONG_PASSWORD)
        self.url = reverse("auth-password-change")
        self.client.post(
            reverse("auth-login"), {"email": self.user.email, "password": STRONG_PASSWORD}, format="json"
        )

    def test_requires_correct_current_password(self):
        response = self.client.post(
            self.url, {"current_password": "wrong", "new_password": NEW_PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(STRONG_PASSWORD))

    def test_rejects_weak_new_password(self):
        response = self.client.post(
            self.url, {"current_password": STRONG_PASSWORD, "new_password": "short"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_success_updates_password_and_timestamp(self):
        response = self.client.post(
            self.url, {"current_password": STRONG_PASSWORD, "new_password": NEW_PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertIsNotNone(self.user.password_changed_at)
        self.assertTrue(SecurityEvent.objects.filter(event="password_changed", user=self.user).exists())

    def test_keeps_current_session_ends_others(self):
        other_client = APIClient()
        other_client.post(
            reverse("auth-login"), {"email": self.user.email, "password": STRONG_PASSWORD}, format="json"
        )
        self.assertEqual(other_client.get(reverse("auth-me")).status_code, status.HTTP_200_OK)

        self.client.post(
            self.url, {"current_password": STRONG_PASSWORD, "new_password": NEW_PASSWORD}, format="json"
        )

        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_200_OK)
        # 403, not 401 - see the comment in test_login.py's test_logout_ends_session.
        self.assertEqual(other_client.get(reverse("auth-me")).status_code, status.HTTP_403_FORBIDDEN)


class PasswordResetTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="reset@example.com", password=STRONG_PASSWORD)
        self.request_url = reverse("auth-password-reset")
        self.confirm_url = reverse("auth-password-reset-confirm")

    def test_request_gives_identical_response_whether_or_not_account_exists(self):
        real_response = self.client.post(self.request_url, {"email": self.user.email}, format="json")
        fake_response = self.client.post(
            self.request_url, {"email": "nobody@example.com"}, format="json"
        )
        self.assertEqual(real_response.status_code, fake_response.status_code)
        self.assertEqual(real_response.data, fake_response.data)
        self.assertEqual(len(mail.outbox), 1)

    def test_confirm_success_changes_password(self):
        self.client.post(self.request_url, {"email": self.user.email}, format="json")
        link = extract_link(mail.outbox[0].body, "/reset-password")
        query = extract_query(link)

        response = self.client.post(
            self.confirm_url,
            {"uid": query["uid"], "token": query["token"], "new_password": NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertTrue(
            SecurityEvent.objects.filter(event="password_reset_done", user=self.user).exists()
        )

    def test_confirm_rejects_bad_token(self):
        self.client.post(self.request_url, {"email": self.user.email}, format="json")
        link = extract_link(mail.outbox[0].body, "/reset-password")
        query = extract_query(link)

        response = self.client.post(
            self.confirm_url,
            {"uid": query["uid"], "token": "garbage", "new_password": NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_cannot_be_reused(self):
        self.client.post(self.request_url, {"email": self.user.email}, format="json")
        link = extract_link(mail.outbox[0].body, "/reset-password")
        query = extract_query(link)
        payload = {"uid": query["uid"], "token": query["token"], "new_password": NEW_PASSWORD}

        first = self.client.post(self.confirm_url, payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.post(
            self.confirm_url, {**payload, "new_password": "Something3lseEntirely!"}, format="json"
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_ends_all_sessions(self):
        logged_in_client = APIClient()
        logged_in_client.post(
            reverse("auth-login"), {"email": self.user.email, "password": STRONG_PASSWORD}, format="json"
        )
        self.assertEqual(
            logged_in_client.get(reverse("auth-me")).status_code, status.HTTP_200_OK
        )

        self.client.post(self.request_url, {"email": self.user.email}, format="json")
        link = extract_link(mail.outbox[0].body, "/reset-password")
        query = extract_query(link)
        self.client.post(
            self.confirm_url,
            {"uid": query["uid"], "token": query["token"], "new_password": NEW_PASSWORD},
            format="json",
        )

        # 403, not 401 - see the comment in test_login.py's test_logout_ends_session.
        self.assertEqual(
            logged_in_client.get(reverse("auth-me")).status_code, status.HTTP_403_FORBIDDEN
        )
