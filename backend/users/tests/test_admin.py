from io import StringIO

from axes.models import AccessAttempt
from django.contrib import admin as admin_site
from django.core import mail
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from users.admin import SecurityEventAdmin
from users.management.commands.seed_users import DEFAULT_PASSWORD, DEMO_USERS
from users.models import Plan, Profile, SecurityEvent, User

from .helpers import STRONG_PASSWORD, make_user


class AdminAccessTests(TestCase):
    def test_only_staff_reach_admin(self):
        self.client.force_login(make_user("regular@example.com"))
        response = self.client.get(reverse("admin:index"))
        self.assertRedirects(response, f"{reverse('admin:login')}?next={reverse('admin:index')}")

        self.client.force_login(make_user("staff@example.com", is_staff=True))
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)

    def test_creating_a_user_in_admin_creates_profile_and_subscription(self):
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password=STRONG_PASSWORD))
        response = self.client.post(
            reverse("admin:users_user_add"),
            {"email": "fromadmin@example.com", "password1": STRONG_PASSWORD, "password2": STRONG_PASSWORD},
        )
        self.assertEqual(response.status_code, 302, response.content[:2000])
        user = User.objects.get(email="fromadmin@example.com")
        self.assertTrue(Profile.objects.filter(pk=user.pk).exists())
        self.assertEqual(user.subscription.plan.slug, "free")

    def test_change_page_shows_profile_and_plan_inlines(self):
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password=STRONG_PASSWORD))
        target = make_user("target@example.com")
        response = self.client.get(reverse("admin:users_user_change", args=[target.pk]))
        self.assertContains(response, 'name="profile-0-timezone"')
        self.assertContains(response, 'name="subscription-0-plan"')


class AdminActionTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password=STRONG_PASSWORD))
        self.target = make_user("target@example.com")

    def _run(self, action):
        return self.client.post(
            reverse("admin:users_user_changelist"), {"action": action, "_selected_action": [self.target.pk]}, follow=True
        )

    def _target_session(self):
        client = APIClient()
        client.force_login(self.target)
        return client

    def test_deactivate_ends_sessions_and_reactivate_restores(self):
        session = self._target_session()
        self._run("deactivate_users")
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)
        self.assertEqual(session.get(reverse("users:me")).status_code, 403)
        self._run("reactivate_users")
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)
        events = set(SecurityEvent.objects.filter(user=self.target).values_list("event", flat=True))
        self.assertTrue({"deactivated", "reactivated"} <= events)

    def test_mark_verified_send_reset_unlock_end_sessions(self):
        self._run("mark_email_verified")
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_email_verified)

        self._run("send_password_reset")
        self.assertEqual(mail.outbox[-1].to, [self.target.email])

        AccessAttempt.objects.create(username=self.target.email, ip_address="127.0.0.1", failures_since_start=5)
        self._run("unlock_users")
        self.assertFalse(AccessAttempt.objects.filter(username=self.target.email).exists())

        session = self._target_session()
        self._run("end_sessions")
        self.assertEqual(session.get(reverse("users:me")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)  # staff stays in

    def test_plan_and_security_event_admin(self):
        self.assertContains(self.client.get(reverse("admin:users_plan_changelist")), "Free")
        site_admin = SecurityEventAdmin(SecurityEvent, admin_site.site)
        self.assertFalse(site_admin.has_add_permission(None))
        self.assertFalse(site_admin.has_change_permission(None))
        self.assertFalse(site_admin.has_delete_permission(None))
        self.assertTrue(Plan.objects.exists())


@override_settings(DEBUG=True)
class SeedUsersTests(TestCase):
    def _run(self, *args):
        call_command("seed_users", *args, stdout=StringIO())

    def test_creates_each_demo_user_and_is_idempotent(self):
        self._run()
        erin = User.objects.get(email="erin@example.com")
        erin.is_active = True
        erin.save()
        self._run()
        self.assertEqual(User.objects.count(), len(DEMO_USERS))
        erin.refresh_from_db()
        self.assertFalse(erin.is_active)
        self.assertTrue(erin.check_password(DEFAULT_PASSWORD))
        self.assertFalse(User.objects.get(email="dave@example.com").is_email_verified)
        self.assertEqual(User.objects.get(email="carol@example.com").profile.base_currency, "AUD")

    def test_leaves_other_accounts_alone(self):
        real = make_user("real@example.com")
        self._run()
        real.refresh_from_db()
        self.assertTrue(real.check_password(STRONG_PASSWORD))

    @override_settings(DEBUG=False)
    def test_refuses_without_debug(self):
        with self.assertRaises(CommandError):
            self._run()
