from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import SecurityEvent, User

from .helpers import STRONG_PASSWORD, extract_link, extract_query


class RegistrationTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("auth-register")

    def test_register_creates_inactive_unverified_user_and_sends_email(self):
        response = self.client.post(
            self.url,
            {"email": "new@example.com", "password": STRONG_PASSWORD, "display_name": "New"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = User.objects.get(email="new@example.com")
        self.assertTrue(user.is_active)  # unverified users may still log in, per PLAN.md
        self.assertFalse(user.is_email_verified)
        self.assertEqual(user.profile.display_name, "New")

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(SecurityEvent.objects.filter(event="register", user=user).exists())

    def test_register_existing_email_gives_identical_response_and_sends_nothing(self):
        User.objects.create_user(email="dup@example.com", password=STRONG_PASSWORD)

        fresh_response = self.client.post(
            self.url, {"email": "brandnew@example.com", "password": STRONG_PASSWORD}, format="json"
        )
        mail.outbox.clear()

        dup_response = self.client.post(
            self.url, {"email": "dup@example.com", "password": STRONG_PASSWORD}, format="json"
        )

        self.assertEqual(dup_response.status_code, fresh_response.status_code)
        self.assertEqual(dup_response.data, fresh_response.data)
        self.assertEqual(len(mail.outbox), 0)  # no second account, no email sent
        self.assertEqual(User.objects.filter(email="dup@example.com").count(), 1)

    def test_register_does_not_log_the_caller_in(self):
        self.client.post(
            self.url, {"email": "new2@example.com", "password": STRONG_PASSWORD}, format="json"
        )
        me_response = self.client.get(reverse("auth-me"))
        # 403, not 401 - see the comment in test_login.py's test_logout_ends_session.
        self.assertEqual(me_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            self.url, {"email": "weak@example.com", "password": "short"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="weak@example.com").exists())

    def test_register_rejects_password_similar_to_email(self):
        response = self.client.post(
            self.url,
            {"email": "joshgrein@example.com", "password": "joshgrein@example.com123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class VerifyEmailTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="verify@example.com", password=STRONG_PASSWORD)

        from accounts.emails import send_verification_email

        send_verification_email(self.user)
        link = extract_link(mail.outbox[0].body, "/verify-email")
        self.query = extract_query(link)

    def test_verify_email_confirms_account(self):
        response = self.client.post(reverse("auth-verify-email"), self.query, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

    def test_verify_email_rejects_bad_token(self):
        bad_query = {**self.query, "token": "not-a-real-token"}
        response = self.client.post(reverse("auth-verify-email"), bad_query, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)

    def test_verify_email_token_is_single_use(self):
        first = self.client.post(reverse("auth-verify-email"), self.query, format="json")
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.post(reverse("auth-verify-email"), self.query, format="json")
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_link_survives_plus_address(self):
        # "+" means a space in a query string - the link must percent-encode
        # it or the SPA reads back "plus addr@example.com" and verification fails.
        from accounts.emails import send_verification_email

        user = User.objects.create_user(email="plus+addr@example.com", password=STRONG_PASSWORD)
        mail.outbox.clear()
        send_verification_email(user)
        query = extract_query(extract_link(mail.outbox[0].body, "/verify-email"))
        self.assertEqual(query["email"], "plus+addr@example.com")

        response = self.client.post(reverse("auth-verify-email"), query, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ResendVerificationTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("auth-resend-verification")

    def test_resend_gives_identical_response_whether_or_not_account_exists(self):
        real_user = User.objects.create_user(email="real@example.com", password=STRONG_PASSWORD)

        real_response = self.client.post(self.url, {"email": real_user.email}, format="json")
        fake_response = self.client.post(self.url, {"email": "nobody@example.com"}, format="json")

        self.assertEqual(real_response.status_code, fake_response.status_code)
        self.assertEqual(real_response.data, fake_response.data)
        self.assertEqual(len(mail.outbox), 1)  # only the real account got one
