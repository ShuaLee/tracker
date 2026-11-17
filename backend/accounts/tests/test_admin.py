from django.contrib import admin as admin_site
from django.test import TestCase
from django.urls import reverse

from accounts.admin import SecurityEventAdmin
from accounts.models import Profile, SecurityEvent, User

from .helpers import STRONG_PASSWORD


class AdminAccessTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            email="admin@example.com", password=STRONG_PASSWORD
        )
        self.staff = User.objects.create_user(
            email="staff@example.com", password=STRONG_PASSWORD, is_staff=True
        )
        self.regular = User.objects.create_user(
            email="regular@example.com", password=STRONG_PASSWORD
        )

    def test_createsuperuser_prompts_only_email_and_password(self):
        self.assertEqual(User.USERNAME_FIELD, "email")
        self.assertEqual(User.REQUIRED_FIELDS, [])

    def test_regular_user_cannot_reach_admin(self):
        self.client.force_login(self.regular)
        response = self.client.get(reverse("admin:index"))
        # Not staff - redirected to the admin login page, not let in.
        self.assertRedirects(
            response, f"{reverse('admin:login')}?next={reverse('admin:index')}"
        )

    def test_staff_user_can_reach_admin(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)

    def test_creating_user_through_admin_creates_a_profile(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("admin:accounts_user_add"),
            {
                "email": "fromadmin@example.com",
                "password1": STRONG_PASSWORD,
                "password2": STRONG_PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 302, response.content)
        new_user = User.objects.get(email="fromadmin@example.com")
        self.assertTrue(Profile.objects.filter(pk=new_user.pk).exists())


class AdminActionTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            email="admin@example.com", password=STRONG_PASSWORD
        )
        self.client.force_login(self.superuser)
        self.target = User.objects.create_user(
            email="target@example.com", password=STRONG_PASSWORD
        )
        self.changelist_url = reverse("admin:accounts_user_changelist")

    def _run_action(self, action):
        return self.client.post(
            self.changelist_url,
            {"action": action, "_selected_action": [str(self.target.pk)]},
            follow=True,
        )

    def test_deactivate_and_reactivate_actions(self):
        self._run_action("deactivate_users")
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)

        self._run_action("reactivate_users")
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)

    def test_mark_email_verified_action(self):
        self.assertIsNone(self.target.email_verified_at)
        self._run_action("mark_email_verified")
        self.target.refresh_from_db()
        self.assertIsNotNone(self.target.email_verified_at)

    def test_send_password_reset_email_action(self):
        from django.core import mail

        self._run_action("send_password_reset_email_action")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.target.email])

    def test_unlock_action_clears_lockout_records(self):
        from axes.models import AccessAttempt

        AccessAttempt.objects.create(
            username=self.target.email,
            ip_address="127.0.0.1",
            failures_since_start=5,
        )
        self.assertTrue(AccessAttempt.objects.filter(username=self.target.email).exists())

        self._run_action("unlock_users")
        self.assertFalse(AccessAttempt.objects.filter(username=self.target.email).exists())


class SecurityEventAdminTests(TestCase):
    def test_read_only(self):
        site_admin = SecurityEventAdmin(SecurityEvent, admin_site.site)
        self.assertFalse(site_admin.has_add_permission(None))
        self.assertFalse(site_admin.has_change_permission(None))
        self.assertFalse(site_admin.has_delete_permission(None))
