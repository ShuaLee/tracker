from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import SecurityEvent

from .helpers import NEW_PASSWORD, STRONG_PASSWORD, AuthAPITestCase, extract_link, extract_query, make_user

CHANGE = reverse("users:password-change")
RESET = reverse("users:password-reset")
CONFIRM = reverse("users:password-reset-confirm")
ME = reverse("users:me")


class ChangePasswordTests(AuthAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("change@example.com")
        self.login(self.user)

    def test_requires_correct_current_password(self):
        response = self.client.post(CHANGE, {"current_password": "wrong", "new_password": NEW_PASSWORD}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"detail": "Your current password is incorrect."})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(STRONG_PASSWORD))

    def test_rejects_weak_new_password(self):
        response = self.client.post(CHANGE, {"current_password": STRONG_PASSWORD, "new_password": "short"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.data)

    def test_success_keeps_this_session_and_ends_others(self):
        other = APIClient()
        self.login(self.user, client=other)
        self.assertEqual(other.get(ME).status_code, status.HTTP_200_OK)

        response = self.client.post(
            CHANGE, {"current_password": STRONG_PASSWORD, "new_password": NEW_PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertIsNotNone(self.user.password_changed_at)
        self.assertTrue(SecurityEvent.objects.filter(event="password_changed", user=self.user).exists())

        self.assertEqual(self.client.get(ME).status_code, status.HTTP_200_OK)
        self.assertEqual(other.get(ME).status_code, status.HTTP_403_FORBIDDEN)


class PasswordResetTests(AuthAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("reset@example.com")

    def _reset_link_query(self):
        self.client.post(RESET, {"email": self.user.email}, format="json")
        return extract_query(extract_link(mail.outbox[-1].body, "/reset-password"))

    def test_request_gives_identical_response_whether_or_not_account_exists(self):
        real = self.client.post(RESET, {"email": self.user.email}, format="json")
        fake = self.client.post(RESET, {"email": "nobody@example.com"}, format="json")
        self.assertEqual((real.status_code, real.data), (fake.status_code, fake.data))
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(SecurityEvent.objects.filter(event="password_reset_requested", user=self.user).exists())

    def test_confirm_sets_password_and_ends_all_sessions(self):
        logged_in = APIClient()
        self.login(self.user, client=logged_in)
        query = self._reset_link_query()

        response = self.client.post(
            CONFIRM, {"uid": query["uid"], "token": query["token"], "new_password": NEW_PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertEqual(logged_in.get(ME).status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(SecurityEvent.objects.filter(event="password_reset_done", user=self.user).exists())

    def test_confirm_rejects_bad_token_and_weak_password(self):
        query = self._reset_link_query()
        bad_token = self.client.post(
            CONFIRM, {"uid": query["uid"], "token": "garbage", "new_password": NEW_PASSWORD}, format="json"
        )
        weak = self.client.post(
            CONFIRM, {"uid": query["uid"], "token": query["token"], "new_password": "short"}, format="json"
        )
        self.assertEqual(bad_token.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(weak.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", weak.data)

    def test_token_cannot_be_reused(self):
        query = self._reset_link_query()
        payload = {"uid": query["uid"], "token": query["token"], "new_password": NEW_PASSWORD}
        self.assertEqual(self.client.post(CONFIRM, payload, format="json").status_code, status.HTTP_200_OK)
        payload["new_password"] = "Something3lseEntirely!"
        self.assertEqual(self.client.post(CONFIRM, payload, format="json").status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_expires(self):
        query = self._reset_link_query()
        with self.settings(PASSWORD_RESET_TIMEOUT=-1):
            response = self.client.post(
                CONFIRM, {"uid": query["uid"], "token": query["token"], "new_password": NEW_PASSWORD}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
