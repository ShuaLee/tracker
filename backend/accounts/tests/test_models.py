from django.test import TestCase

from accounts.models import Profile, User

from .helpers import STRONG_PASSWORD


class UserManagerTests(TestCase):
    def test_create_user_lowercases_email(self):
        user = User.objects.create_user(email="Mixed.Case@Example.com", password=STRONG_PASSWORD)
        self.assertEqual(user.email, "mixed.case@example.com")

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password=STRONG_PASSWORD)

    def test_create_user_defaults(self):
        user = User.objects.create_user(email="a@example.com", password=STRONG_PASSWORD)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_email_verified)

    def test_create_superuser_defaults(self):
        user = User.objects.create_superuser(email="root@example.com", password=STRONG_PASSWORD)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_rejects_is_staff_false(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="root2@example.com", password=STRONG_PASSWORD, is_staff=False
            )

    def test_create_superuser_rejects_is_superuser_false(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="root3@example.com", password=STRONG_PASSWORD, is_superuser=False
            )


class UserModelTests(TestCase):
    def test_str_is_email(self):
        user = User.objects.create_user(email="a@example.com", password=STRONG_PASSWORD)
        self.assertEqual(str(user), "a@example.com")

    def test_save_normalizes_email_outside_the_manager_too(self):
        user = User.objects.create_user(email="a@example.com", password=STRONG_PASSWORD)
        user.email = "A@Example.com"
        user.save()
        self.assertEqual(user.email, "a@example.com")


class ProfileSignalTests(TestCase):
    def test_profile_created_automatically(self):
        user = User.objects.create_user(email="a@example.com", password=STRONG_PASSWORD)
        self.assertTrue(Profile.objects.filter(pk=user.pk).exists())
        self.assertEqual(user.profile.role, Profile.Role.INDIVIDUAL)
        self.assertEqual(user.profile.base_currency, Profile.Currency.CAD)

    def test_two_admin_created_users_each_get_their_own_profile(self):
        u1 = User.objects.create_user(email="one@example.com", password=STRONG_PASSWORD)
        u2 = User.objects.create_user(email="two@example.com", password=STRONG_PASSWORD)
        self.assertNotEqual(u1.profile.pk, u2.profile.pk)


class ProfileValidationTests(TestCase):
    def setUp(self):
        self.profile = User.objects.create_user(email="tz@example.com", password=STRONG_PASSWORD).profile

    def test_default_timezone_is_valid(self):
        self.profile.full_clean()  # does not raise

    def test_rejects_unknown_timezone(self):
        from django.core.exceptions import ValidationError

        self.profile.timezone = "Not/AZone"
        with self.assertRaises(ValidationError) as ctx:
            self.profile.full_clean()
        self.assertIn("timezone", ctx.exception.message_dict)
