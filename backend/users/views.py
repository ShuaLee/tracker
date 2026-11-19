"""
The /api/auth/ endpoints (PLAN.md step 1). Session authentication with CSRF.

Responses that could reveal whether an email has an account (register,
password reset, resend verification, change email, login errors) are
deliberately identical across branches.
"""

from django.contrib.auth import authenticate, get_user_model, update_session_auth_hash
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import emails
from .audit import log_event
from .models import Currency
from .serializers import (
    ChangeEmailSerializer,
    ChangePasswordSerializer,
    CurrentPasswordSerializer,
    EmailSerializer,
    LoginSerializer,
    LogoutAllSerializer,
    MeSerializer,
    PasswordResetConfirmSerializer,
    RegisterSerializer,
    SecurityEventSerializer,
    VerifyEmailSerializer,
)
from .sessions import end_all_sessions, end_other_sessions
from .throttling import (
    LoginEmailThrottle,
    PasswordResetEmailThrottle,
    RegisterEmailThrottle,
    ResendVerificationEmailThrottle,
)
from .tokens import email_verification_token_generator, for_email
from .validators import available_timezones, validate_user_password

User = get_user_model()

REGISTER_MESSAGE = "If that address can be registered, we've sent a verification link."
RESEND_MESSAGE = "If that address needs verifying, we've sent a new link."
RESET_MESSAGE = "If that address has an account, we've sent a password reset link."
EMAIL_CHANGE_MESSAGE = "If that address is available, we've sent a confirmation link to it."
LOGIN_ERROR = "That email or password is incorrect."
TOKEN_ERROR = "This link is invalid or has expired."
WRONG_PASSWORD_ERROR = "Your current password is incorrect."

SECURITY_EVENTS_LIMIT = 50


def _user_from_uid(uid):
    try:
        return User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None


def _wrong_password():
    return Response({"detail": WRONG_PASSWORD_ERROR}, status=status.HTTP_400_BAD_REQUEST)


class CsrfView(APIView):
    """GET once on load so the SPA has a csrftoken cookie before any POST."""

    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"detail": "CSRF cookie set."})


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle, RegisterEmailThrottle]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = data["email"].lower()

        if not User.objects.filter(email=email).exists():
            with transaction.atomic():
                user = User.objects.create_user(email=email, password=data["password"])
                user.profile.display_name = data["display_name"]
                user.profile.save(update_fields=["display_name", "updated_at"])
            emails.send_verification_email(user)
            log_event("register", request=request, user=user)

        # Same response either way, and never logged in here: doing so only
        # for new accounts would reveal which branch ran.
        return Response({"detail": REGISTER_MESSAGE})


class VerifyEmailView(APIView):
    """Confirms an email - the signup address, or a new address from
    email/change/ (told apart by comparing it with the current email)."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = _user_from_uid(data["uid"])
        target_email = data["email"].lower()
        if user is None or not email_verification_token_generator.check_token(
            for_email(user, target_email), data["token"]
        ):
            return Response({"detail": TOKEN_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        old_email = user.email
        is_change = target_email != old_email
        if is_change and User.objects.exclude(pk=user.pk).filter(email=target_email).exists():
            # Taken by someone else since the link was sent.
            return Response({"detail": TOKEN_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        user.email = target_email
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email", "email_verified_at"])

        if is_change:
            emails.send_email_changed_notice(old_email, user.email)
            log_event("email_changed", request=request, user=user)
        return Response({"detail": "Email confirmed."})


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle, ResendVerificationEmailThrottle]
    throttle_scope = "resend_verification"

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"].lower(), is_active=True).first()
        if user is not None and not user.is_email_verified:
            emails.send_verification_email(user)
        return Response({"detail": RESEND_MESSAGE})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle, LoginEmailThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # The DRF request (not request._request) lets django-axes read the
        # submitted email. Wrong password, inactive account and lockout all
        # return the same generic error.
        user = authenticate(
            request=request,
            email=serializer.validated_data["email"].lower(),
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response({"detail": LOGIN_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        django_login(request, user)  # also rotates the session key and CSRF token
        return Response(MeSerializer(user).data)


class LogoutView(APIView):
    def post(self, request):
        django_logout(request)
        return Response({"detail": "Logged out."})


class LogoutAllView(APIView):
    """Log out everywhere. No password needed: it only takes access away."""

    def post(self, request):
        serializer = LogoutAllSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        log_event("logout_all", request=request, user=user)

        if serializer.validated_data["keep_current"]:
            end_other_sessions(user, except_session_key=request.session.session_key)
            return Response({"detail": "Signed out of every other session."})

        end_all_sessions(user)
        django_logout(request)
        return Response({"detail": "Signed out everywhere."})


class MeView(APIView):
    def get(self, request):
        return Response(MeSerializer(request.user).data)

    def patch(self, request):
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class OptionsView(APIView):
    """Choices for the profile form, so clients never hard-code them."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "currencies": [{"value": value, "label": label} for value, label in Currency.choices],
                "timezones": sorted(available_timezones()),
            }
        )


class SecurityEventsView(APIView):
    """The caller's own recent security activity."""

    def get(self, request):
        events = request.user.security_events.all()[:SECURITY_EVENTS_LIMIT]
        return Response(SecurityEventSerializer(events, many=True).data)


class ChangePasswordView(APIView):
    """Keeps this session, ends every other one."""

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        # Check the current password before reporting on the new one, so a
        # wrong current password never leaks password-rule feedback.
        if not request.user.check_password(request.data.get("current_password") or ""):
            return _wrong_password()
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.password_changed_at = timezone.now()
        user.save(update_fields=["password", "password_changed_at"])

        update_session_auth_hash(request, user)
        end_other_sessions(user, except_session_key=request.session.session_key)
        log_event("password_changed", request=request, user=user)
        return Response({"detail": "Password changed."})


class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle, PasswordResetEmailThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"].lower(), is_active=True).first()
        if user is not None:
            emails.send_password_reset_email(user)
            log_event("password_reset_requested", request=request, user=user)
        return Response({"detail": RESET_MESSAGE})


class PasswordResetConfirmView(APIView):
    """Sets a new password from an emailed link. Ends every session."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = _user_from_uid(data["uid"])
        if user is None or not default_token_generator.check_token(user, data["token"]):
            return Response({"detail": TOKEN_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_user_password(data["new_password"], user)
        except DjangoValidationError as exc:
            return Response({"new_password": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(data["new_password"])
        user.password_changed_at = timezone.now()
        user.save(update_fields=["password", "password_changed_at"])
        end_all_sessions(user)
        log_event("password_reset_done", request=request, user=user)
        return Response({"detail": "Password reset."})


class ChangeEmailView(APIView):
    """Sends a confirmation link to the new address; the email only changes
    once it's clicked (via verify-email/), and the old address is told."""

    def post(self, request):
        serializer = ChangeEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            return _wrong_password()

        new_email = serializer.validated_data["new_email"].lower()
        if new_email != user.email and not User.objects.filter(email=new_email).exists():
            emails.send_email_change_confirmation(user, new_email)
        # Same response whether or not the address is free - otherwise this
        # would let a logged-in user probe for other accounts.
        return Response({"detail": EMAIL_CHANGE_MESSAGE})


class DeleteAccountView(APIView):
    """Permanently deletes the account and everything it owns (profile,
    subscription, portfolio). Requires the current password."""

    def post(self, request):
        serializer = CurrentPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            return _wrong_password()

        # Logged first: the row keeps the email after the user is gone.
        log_event("account_deleted", request=request, user=user)
        end_all_sessions(user)
        django_logout(request)
        user.delete()
        return Response({"detail": "Account deleted."})
