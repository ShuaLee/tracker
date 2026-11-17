"""
DRF's ScopedRateThrottle keys on the caller (user pk, else IP) - that gives
the "N/min per IP" dimension PLAN.md asks for. It can't also give the
"N/hour per account" dimension at the same time, so AccountRateThrottle
keys on the *submitted* email instead, for the views that accept one
(login, register, password reset, resend-verification). Apply both
throttle classes together on those views.
"""

from rest_framework.throttling import SimpleRateThrottle


class AccountRateThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            # No email submitted (e.g. a malformed request) - nothing to
            # rate-limit by account; ScopedRateThrottle's per-IP limit
            # still applies.
            return None
        return self.cache_format % {"scope": self.scope, "ident": email}


class LoginAccountThrottle(AccountRateThrottle):
    scope = "login_account"


class RegisterAccountThrottle(AccountRateThrottle):
    scope = "register_account"


class PasswordResetAccountThrottle(AccountRateThrottle):
    scope = "password_reset_account"


class ResendVerificationAccountThrottle(AccountRateThrottle):
    scope = "resend_verification_account"
