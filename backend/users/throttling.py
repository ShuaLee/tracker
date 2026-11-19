"""
Two throttle dimensions for the public endpoints that take an email (login,
register, password reset, resend verification):

- per IP: DRF's ScopedRateThrottle (the view's `throttle_scope`);
- per submitted email: EmailRateThrottle below, so one account can't be
  hammered by an attacker rotating IPs.

Views list both classes. Rates are in settings REST_FRAMEWORK.
"""

from rest_framework.throttling import SimpleRateThrottle


class EmailRateThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return None  # nothing to key on; the per-IP throttle still applies
        return self.cache_format % {"scope": self.scope, "ident": email}


class LoginEmailThrottle(EmailRateThrottle):
    scope = "login_email"


class RegisterEmailThrottle(EmailRateThrottle):
    scope = "register_email"


class PasswordResetEmailThrottle(EmailRateThrottle):
    scope = "password_reset_email"


class ResendVerificationEmailThrottle(EmailRateThrottle):
    scope = "resend_verification_email"
