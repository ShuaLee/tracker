from django.core.exceptions import ValidationError
from django.test import TestCase

from users.models import Currency, Profile, Subscription, User

from .helpers import STRONG_PASSWORD, make_user


class UserManagerTests(TestCase):
    def test_create_user_lowercases_email_and_sets_defaults(self):
        user = make_user("Mixed.Case@Example.com")
        self.assertEqual(user.email, "mixed.case@example.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_email_verified)
        self.assertTrue(user.check_password(STRONG_PASSWORD))

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password=STRONG_PASSWORD)

    def test_create_superuser(self):
        user = User.objects.create_superuser(email="root@example.com", password=STRONG_PASSWORD)
        self.assertTrue(user.is_staff and user.is_superuser)
        for flag in ("is_staff", "is_superuser"):
            with self.assertRaises(ValueError):
                User.objects.create_superuser(email=f"{flag}@example.com", password=STRONG_PASSWORD, **{flag: False})

    def test_email_is_login_field_and_createsuperuser_asks_nothing_else(self):
        self.assertEqual(User.USERNAME_FIELD, "email")
        self.assertEqual(User.REQUIRED_FIELDS, [])

    def test_save_lowercases_email_outside_the_manager_too(self):
        user = make_user()
        user.email = "Upper@Example.com"
        user.save()
        self.assertEqual(user.email, "upper@example.com")


class CreatedWithUserTests(TestCase):
    def test_profile_and_free_subscription_created_automatically(self):
        user = make_user()
        self.assertEqual(user.profile.base_currency, Currency.CAD)
        self.assertEqual(user.profile.timezone, "America/Toronto")
        self.assertEqual(user.subscription.plan.slug, "free")
        self.assertEqual(user.subscription.status, Subscription.Status.ACTIVE)

    def test_each_user_gets_their_own(self):
        a, b = make_user("a@example.com"), make_user("b@example.com")
        self.assertNotEqual(a.profile.pk, b.profile.pk)
        self.assertEqual(Profile.objects.count(), 2)
        self.assertEqual(Subscription.objects.count(), 2)


class ProfileValidationTests(TestCase):
    def test_rejects_unknown_timezone(self):
        profile = make_user().profile
        profile.full_clean()  # the default is valid
        profile.timezone = "Not/AZone"
        with self.assertRaises(ValidationError) as ctx:
            profile.full_clean()
        self.assertIn("timezone", ctx.exception.message_dict)
