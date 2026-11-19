import re
from urllib.parse import parse_qs, urlparse

from django.core.cache import cache
from rest_framework.test import APITestCase

from users.models import User

# Clears MinimumLength(12) and isn't a dictionary word.
STRONG_PASSWORD = "Tr0ub4dor&3xplosive!"
NEW_PASSWORD = "4n0ther$trongOne99"


def make_user(email="user@example.com", password=STRONG_PASSWORD, **extra):
    return User.objects.create_user(email=email, password=password, **extra)


def extract_link(body, path_fragment):
    match = re.search(rf"(http\S*{re.escape(path_fragment)}\S*)", body)
    assert match, f"No {path_fragment!r} link in email body:\n{body}"
    return match.group(1)


def extract_query(url):
    return {key: values[0] for key, values in parse_qs(urlparse(url).query).items()}


class AuthAPITestCase(APITestCase):
    """Clears the cache before each test: DRF throttle counters live there
    (LocMemCache) and would otherwise leak between tests."""

    def setUp(self):
        cache.clear()

    def login(self, user, password=STRONG_PASSWORD, client=None):
        """Log in through the real endpoint (not force_login), so signals,
        axes and session rotation all run."""
        from django.urls import reverse

        return (client or self.client).post(
            reverse("users:login"), {"email": user.email, "password": password}, format="json"
        )
