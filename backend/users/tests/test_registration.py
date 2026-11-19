from django.core import mail
from django.urls import reverse
from rest_framework import status

from users.emails import send_verification_email
from users.models import SecurityEvent, User

from .helpers import STRONG_PASSWORD, AuthAPITestCase, extract_link, extract_query, make_user

REGISTER = reverse("users:register")
VERIFY = reverse("users:verify-email")
RESEND = reverse("users:resend-verification")


class RegisterTests(AuthAPITestCase):
    def test_creates_unverified_user_with_profile_and_sends_verification(self):
        response = self.client.post(
            REGISTER, {"email": "New@Example.com", "password": STRONG_PASSWORD, "display_name": "New"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(email="new@example.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_email_verified)
        self.assertEqual(user.profile.display_name, "New")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["new@example.com"])
        self.assertTrue(SecurityEvent.objects.filter(event="register", user=user).exists())

    def test_existing_email_gives_identical_response_and_sends_nothing(self):
        make_user("dup@example.com")
        fresh = self.client.post(REGISTER, {"email": "brandnew@example.com", "password": STRONG_PASSWORD}, format="json")
        mail.outbox.clear()
        dup = self.client.post(REGISTER, {"email": "DUP@example.com", "password": STRONG_PASSWORD}, format="json")
        self.assertEqual((dup.status_code, dup.data), (fresh.status_code, fresh.data))
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(User.objects.filter(email="dup@example.com").count(), 1)

    def test_does_not_log_the_caller_in(self):
        self.client.post(REGISTER, {"email": "new@example.com", "password": STRONG_PASSWORD}, format="json")
        # 403, not 401: SessionAuthentication sends no WWW-Authenticate header,
        # so DRF reports "not authenticated" as 403.
        self.assertEqual(self.client.get(reverse("users:me")).status_code, status.HTTP_403_FORBIDDEN)

    def test_rejects_weak_and_similar_passwords(self):
        for email, password in (("weak@example.com", "short"), ("joshgrein@example.com", "joshgrein@example.com123")):
            response = self.client.post(REGISTER, {"email": email, "password": password}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, password)
        self.assertFalse(User.objects.exists())

    def test_rejects_password_similar_to_display_name(self):
        response = self.client.post(
            REGISTER,
            {"email": "x@example.com", "password": "Bartholomew-Smithers", "display_name": "Bartholomew Smithers"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class VerifyEmailTests(AuthAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("verify@example.com")
        send_verification_email(self.user)
        self.query = extract_query(extract_link(mail.outbox[0].body, "/verify-email"))

    def test_confirms_email(self):
        self.assertEqual(self.client.post(VERIFY, self.query, format="json").status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

    def test_rejects_bad_token_and_bad_uid(self):
        for bad in ({**self.query, "token": "nope"}, {**self.query, "uid": "nope"}):
            self.assertEqual(self.client.post(VERIFY, bad, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)

    def test_token_is_single_use(self):
        self.client.post(VERIFY, self.query, format="json")
        self.assertEqual(self.client.post(VERIFY, self.query, format="json").status_code, status.HTTP_400_BAD_REQUEST)

    def test_link_survives_plus_address(self):
        # "+" is a space in a query string; the link must percent-encode it.
        user = make_user("plus+addr@example.com")
        mail.outbox.clear()
        send_verification_email(user)
        query = extract_query(extract_link(mail.outbox[0].body, "/verify-email"))
        self.assertEqual(query["email"], "plus+addr@example.com")
        self.assertEqual(self.client.post(VERIFY, query, format="json").status_code, status.HTTP_200_OK)


class ResendVerificationTests(AuthAPITestCase):
    def test_identical_response_whether_or_not_account_exists(self):
        make_user("real@example.com")
        real = self.client.post(RESEND, {"email": "real@example.com"}, format="json")
        fake = self.client.post(RESEND, {"email": "nobody@example.com"}, format="json")
        self.assertEqual((real.status_code, real.data), (fake.status_code, fake.data))
        self.assertEqual(len(mail.outbox), 1)

    def test_sends_nothing_to_verified_or_inactive_users(self):
        verified = make_user("verified@example.com")
        verified.email_verified_at = verified.date_joined
        verified.save()
        make_user("inactive@example.com", is_active=False)
        for email in ("verified@example.com", "inactive@example.com"):
            self.client.post(RESEND, {"email": email}, format="json")
        self.assertEqual(len(mail.outbox), 0)
