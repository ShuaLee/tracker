from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from holdings.models import Portfolio

from .helpers import make_user, portfolio_of

LIST = reverse("portfolio-list")


def detail(portfolio):
    return reverse("portfolio-detail", args=[portfolio.pk])


class CrossUserIsolationTests(APITestCase):
    """PLAN.md 1.4's most important tests: user A can't touch anything of B's."""

    def setUp(self):
        self.alice = make_user("alice@example.com")
        self.bob = make_user("bob@example.com")
        self.bobs = portfolio_of(self.bob)
        self.client.force_login(self.alice)

    def test_list_shows_only_own(self):
        response = self.client.get(LIST)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([p["id"] for p in response.data], [portfolio_of(self.alice).pk])

    def test_cannot_read_or_update_others_and_gets_404(self):
        self.assertEqual(self.client.get(detail(self.bobs)).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.patch(detail(self.bobs), {"name": "pwned"}, format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.bobs.refresh_from_db()
        self.assertEqual(self.bobs.name, "My portfolio")

    def test_404_for_others_matches_404_for_nonexistent(self):
        missing = reverse("portfolio-detail", args=[999_999])
        self.assertEqual(self.client.get(missing).data, self.client.get(detail(self.bobs)).data)

    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(LIST).status_code, status.HTTP_403_FORBIDDEN)


class OnePortfolioPerUserTests(APITestCase):
    """Each user has exactly one portfolio, made at signup - no create or
    delete through the API."""

    def setUp(self):
        self.user = make_user("me@example.com")
        self.portfolio = portfolio_of(self.user)
        self.client.force_login(self.user)

    def test_create_is_not_available(self):
        response = self.client.post(LIST, {"name": "Second"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(Portfolio.objects.filter(owner=self.user).count(), 1)

    def test_delete_is_not_available(self):
        response = self.client.delete(detail(self.portfolio))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Portfolio.objects.filter(pk=self.portfolio.pk).exists())

    def test_put_is_not_available(self):
        response = self.client.put(detail(self.portfolio), {"name": "x"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class UpdateTests(APITestCase):
    def setUp(self):
        self.user = make_user("me@example.com")
        self.portfolio = portfolio_of(self.user)
        self.client.force_login(self.user)

    def test_owner_reads_own_portfolio(self):
        response = self.client.get(detail(self.portfolio))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {k: response.data[k] for k in ("id", "name", "base_currency")},
            {"id": self.portfolio.pk, "name": "My portfolio", "base_currency": "CAD"},
        )

    def test_owner_can_rename_and_change_currency(self):
        response = self.client.patch(
            detail(self.portfolio), {"name": "Family money", "base_currency": "USD"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.portfolio.refresh_from_db()
        self.assertEqual((self.portfolio.name, self.portfolio.base_currency), ("Family money", "USD"))

    def test_rejects_blank_name_and_invalid_currency(self):
        for body in ({"name": ""}, {"base_currency": "XYZ"}):
            response = self.client.patch(detail(self.portfolio), body, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, body)

    def test_read_only_fields_are_ignored(self):
        other = make_user("other@example.com")
        response = self.client.patch(detail(self.portfolio), {"id": 12345, "owner": other.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.owner, self.user)
        self.assertEqual(response.data["id"], self.portfolio.pk)
