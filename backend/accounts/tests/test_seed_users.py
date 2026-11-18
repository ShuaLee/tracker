from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from accounts.management.commands.seed_users import DEFAULT_PASSWORD, DEMO_USERS
from accounts.models import User


@override_settings(DEBUG=True)
class SeedUsersTests(TestCase):
    def _run(self, *args):
        call_command("seed_users", *args, stdout=StringIO())

    def test_creates_each_demo_user_in_its_listed_state(self):
        self._run()
        self.assertEqual(User.objects.count(), len(DEMO_USERS))

        carol = User.objects.get(email="carol@example.com")
        self.assertEqual(carol.profile.role, "advisor")
        self.assertTrue(carol.check_password(DEFAULT_PASSWORD))
        self.assertFalse(User.objects.get(email="dave@example.com").is_email_verified)
        self.assertFalse(User.objects.get(email="erin@example.com").is_active)
        self.assertFalse(carol.is_staff)

    def test_idempotent_and_resets_changed_state(self):
        self._run()
        erin = User.objects.get(email="erin@example.com")
        erin.is_active = True
        erin.set_password("SomethingElse123!")
        erin.save()

        self._run()
        erin.refresh_from_db()
        self.assertEqual(User.objects.count(), len(DEMO_USERS))
        self.assertFalse(erin.is_active)
        self.assertTrue(erin.check_password(DEFAULT_PASSWORD))

    def test_custom_password(self):
        self._run("--password", "AnotherPass456!")
        self.assertTrue(User.objects.get(email="alice@example.com").check_password("AnotherPass456!"))

    def test_leaves_other_accounts_alone(self):
        real = User.objects.create_user(email="real@example.com", password="RealPassword123!")
        self._run()
        real.refresh_from_db()
        self.assertTrue(real.check_password("RealPassword123!"))

    @override_settings(DEBUG=False)
    def test_refuses_without_debug(self):
        with self.assertRaises(CommandError):
            self._run()
        self.assertEqual(User.objects.count(), 0)
