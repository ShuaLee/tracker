from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from holdings import access
from holdings.models import PortfolioAccess

from .helpers import grant, make_user, portfolio_of

Role = PortfolioAccess.Role


class AccessibleAndRoleTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.portfolio = portfolio_of(self.owner)
        self.manager = make_user("manager@example.com")
        self.viewer = make_user("viewer@example.com")
        self.revoked = make_user("revoked@example.com")
        grant(self.portfolio, self.manager, Role.MANAGER)
        grant(self.portfolio, self.viewer, Role.VIEWER)
        grant(self.portfolio, self.revoked, Role.MANAGER, status=PortfolioAccess.Status.REVOKED)

    def _ids(self, user, min_role=access.READ):
        return set(access.accessible_portfolios(user, min_role).values_list("pk", flat=True))

    def test_each_user_sees_own_plus_shared(self):
        self.assertEqual(self._ids(self.owner), {self.portfolio.pk})
        self.assertEqual(self._ids(self.viewer), {self.portfolio.pk, portfolio_of(self.viewer).pk})

    def test_min_role_filters(self):
        self.assertIn(self.portfolio.pk, self._ids(self.manager, access.EDIT))
        self.assertNotIn(self.portfolio.pk, self._ids(self.viewer, access.EDIT))
        self.assertNotIn(self.portfolio.pk, self._ids(self.manager, access.OWN))
        self.assertIn(self.portfolio.pk, self._ids(self.owner, access.OWN))

    def test_revoked_row_gives_nothing(self):
        self.assertNotIn(self.portfolio.pk, self._ids(self.revoked))
        self.assertIsNone(access.role_for(self.revoked, self.portfolio))

    def test_my_role_annotation(self):
        roles = {
            user.email: access.accessible_portfolios(user).get(pk=self.portfolio.pk).my_role
            for user in (self.owner, self.manager, self.viewer)
        }
        self.assertEqual(
            roles,
            {"owner@example.com": "owner", "manager@example.com": "manager", "viewer@example.com": "viewer"},
        )

    def test_anonymous_and_inactive_users_see_nothing(self):
        self.assertFalse(access.accessible_portfolios(AnonymousUser()).exists())
        self.owner.is_active = False
        self.owner.save()
        self.assertFalse(access.accessible_portfolios(self.owner).exists())
        self.assertIsNone(access.role_for(self.owner, self.portfolio))

    def test_has_role(self):
        self.assertTrue(access.has_role(Role.OWNER, access.EDIT))
        self.assertTrue(access.has_role(Role.MANAGER, access.EDIT))
        self.assertFalse(access.has_role(Role.VIEWER, access.EDIT))
        self.assertFalse(access.has_role(None, access.READ))
