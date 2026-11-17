from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import SecurityEvent, User

from .helpers import STRONG_PASSWORD, extract_link, extract_query


class EmailChangeTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="old@example.com", password=STRONG_PASSWORD)
        self.url = reverse("auth-email-change")
        self.client.post(
            reverse("auth-login"), {"email": self.user.email, "password": STRONG_PASSWORD}, format="json"
        )

    def test_requires_correct_password(self):
        response = self.client.post(
            self.url, {"new_email": "new@example.com", "current_password": "wrong"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_sends_confirmation_to_new_address_only(self):
        response = self.client.post(
            self.url,
            {"new_email": "new@example.com", "current_password": STRONG_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["new@example.com"])

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")  # not changed yet

    def test_confirming_updates_email_and_notifies_old_address(self):
        self.client.post(
            self.url,
            {"new_email": "new@example.com", "current_password": STRONG_PASSWORD},
            format="json",
        )
        link = extract_link(mail.outbox[0].body, "/verify-email")
        query = extract_query(link)
        mail.outbox.clear()

        response = self.client.post(reverse("auth-verify-email"), query, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")
        self.assertTrue(self.user.is_email_verified)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["old@example.com"])
        self.assertTrue(
            SecurityEvent.objects.filter(event="email_changed", user=self.user).exists()
        )

    def test_taken_address_gives_generic_response_and_sends_nothing(self):
        User.objects.create_user(email="taken@example.com", password=STRONG_PASSWORD)

        response = self.client.post(
            self.url,
            {"new_email": "taken@example.com", "current_password": STRONG_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)
