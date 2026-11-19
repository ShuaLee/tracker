"""Change email and delete account."""

from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import Profile, SecurityEvent, Subscription, User

from .helpers import STRONG_PASSWORD, AuthAPITestCase, extract_link, extract_query, make_user

CHANGE_EMAIL = reverse("users:email-change")
DELETE = reverse("users:delete-account")
ME = reverse("users:me")


class ChangeEmailTests(AuthAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("old@example.com")
        self.login(self.user)

    def _request(self, new_email, password=STRONG_PASSWORD):
        return self.client.post(CHANGE_EMAIL, {"new_email": new_email, "current_password": password}, format="json")

    def test_requires_correct_password(self):
        self.assertEqual(self._request("new@example.com", password="wrong").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_sends_confirmation_to_new_address_only_and_changes_nothing_yet(self):
        self.assertEqual(self._request("New@Example.com").status_code, status.HTTP_200_OK)
        self.assertEqual([m.to for m in mail.outbox], [["new@example.com"]])
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")

    def test_confirming_changes_email_verifies_it_and_notifies_old_address(self):
        self._request("new@example.com")
        query = extract_query(extract_link(mail.outbox[0].body, "/verify-email"))
        mail.outbox.clear()

        self.assertEqual(self.client.post(reverse("users:verify-email"), query, format="json").status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")
        self.assertTrue(self.user.is_email_verified)
        self.assertEqual([m.to for m in mail.outbox], [["old@example.com"]])
        self.assertTrue(SecurityEvent.objects.filter(event="email_changed", user=self.user).exists())

    def test_taken_address_gives_same_response_and_sends_nothing(self):
        make_user("taken@example.com")
        free = self._request("free@example.com")
        mail.outbox.clear()
        taken = self._request("taken@example.com")
        self.assertEqual((taken.status_code, taken.data), (free.status_code, free.data))
        self.assertEqual(len(mail.outbox), 0)

    def test_link_fails_if_address_was_taken_meanwhile(self):
        self._request("race@example.com")
        query = extract_query(extract_link(mail.outbox[0].body, "/verify-email"))
        make_user("race@example.com")
        self.assertEqual(self.client.post(reverse("users:verify-email"), query, format="json").status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")


class DeleteAccountTests(AuthAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("bye@example.com")
        self.login(self.user)

    def test_requires_correct_password(self):
        response = self.client.post(DELETE, {"current_password": "wrong"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_deletes_user_and_everything_they_own_and_ends_every_session(self):
        other_device = APIClient()
        self.login(self.user, client=other_device)
        user_pk = self.user.pk

        response = self.client.post(DELETE, {"current_password": STRONG_PASSWORD}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(pk=user_pk).exists())
        self.assertFalse(Profile.objects.filter(pk=user_pk).exists())
        self.assertFalse(Subscription.objects.filter(pk=user_pk).exists())
        self.assertEqual(self.client.get(ME).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(other_device.get(ME).status_code, status.HTTP_403_FORBIDDEN)

    def test_audit_row_outlives_the_account(self):
        self.client.post(DELETE, {"current_password": STRONG_PASSWORD}, format="json")
        event = SecurityEvent.objects.get(event="account_deleted")
        self.assertIsNone(event.user)
        self.assertEqual(event.email, "bye@example.com")

    def test_requires_login(self):
        response = APIClient().post(DELETE, {"current_password": STRONG_PASSWORD}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
