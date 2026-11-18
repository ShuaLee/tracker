from django.contrib.auth import (
    authenticate,
    get_user_model,
    login as django_login,
    logout as django_logout,
    update_session_auth_hash,
)
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
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

from .audit import log_event
from .emails import (
    send_email_change_confirmation,
    send_email_changed_notice,
    send_password_reset_email,
    send_verification_email,
)
from .models import Profile
from .serializers import (
    ChangePasswordSerializer,
    DeactivateSerializer,
    EmailChangeSerializer,
    LoginSerializer,
    LogoutAllSerializer,
    MeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    SecurityEventSerializer,
    VerifyEmailSerializer,
)
from .sessions import end_all_sessions, end_other_sessions
from .throttling import (
    LoginAccountThrottle,
    PasswordResetAccountThrottle,
    RegisterAccountThrottle,
    ResendVerificationAccountThrottle,
)
from .tokens import email_verification_token_generator, for_email
from .validation import available_timezones, validate_user_password

User = get_user_model()

# How many of a user's own SecurityEvents security-events/ returns.
SECURITY_EVENTS_LIMIT = 50

# Deliberately identical across branches that must not be told apart from
# the outside (does this email exist / is it already verified / etc).
REGISTER_MESSAGE = "If that address can be registered, we've sent a verification link."
RESET_MESSAGE = "If that address has an account, we've sent a password reset link."
RESEND_MESSAGE = "If that address needs verifying, we've sent a new link."
LOGIN_ERROR = "That email or password is incorrect."
TOKEN_ERROR = "This link is invalid or has expired."
EMAIL_CHANGE_MESSAGE = "If that address is available, we've sent a confirmation link."
WRONG_PASSWORD_ERROR = "Your current password is incorrect."


def _decode_uid(uid):
    try:
        return User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None


def _password_strength_error(password, user):
    """
    validate_user_password() raises django.core.exceptions.ValidationError.
    Inside a serializer's validate() DRF catches that automatically; these
    two views call it directly, so they need to catch it themselves. Returns
    a 400 Response if the password is too weak, else None.
    """
    try:
        validate_user_password(password, user)
    except DjangoValidationError as exc:
        return Response({"new_password": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
    return None


class CsrfCookieView(APIView):
    """GET once on load to get a CSRF cookie set before any POST."""

    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"detail": "CSRF cookie set."})


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle, RegisterAccountThrottle]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()

        if not User.objects.filter(email=email).exists():
            user = User.objects.create_user(
                email=email,
                password=serializer.validated_data["password"],
            )
            user.profile.display_name = serializer.validated_data["display_name"]
            user.profile.save()
            send_verification_email(user)
            log_event("register", request=request, user=user)

        # Same response whether or not the email was already registered -
        # and we never log the caller in here, since doing so only on the
        # "new account" branch would itself reveal which branch was taken.
        return Response({"detail": REGISTER_MESSAGE})


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = _decode_uid(data["uid"])
        if user is None:
            return Response({"detail": TOKEN_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        target_email = data["email"].lower()
        if not email_verification_token_generator.check_token(
            for_email(user, target_email), data["token"]
        ):
            return Response({"detail": TOKEN_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        is_email_change = target_email != user.email
        if is_email_change:
            if User.objects.exclude(pk=user.pk).filter(email=target_email).exists():
                # Someone else claimed it between the link being sent and
                # used - fail the same way an expired link would.
                return Response({"detail": TOKEN_ERROR}, status=status.HTTP_400_BAD_REQUEST)
            old_email = user.email
            user.email = target_email

        user.email_verified_at = timezone.now()
        user.save()

        if is_email_change:
            send_email_changed_notice(old_email, user.email)
            log_event("email_changed", request=request, user=user)

        return Response({"detail": "Email confirmed."})


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle, ResendVerificationAccountThrottle]
    throttle_scope = "resend_verification"

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()

        user = User.objects.filter(email=email, is_active=True).first()
        if user and not user.is_email_verified:
            send_verification_email(user)

        return Response({"detail": RESEND_MESSAGE})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle, LoginAccountThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        password = serializer.validated_data["password"]

        # Passing the DRF request (not request._request) lets django-axes
        # read the submitted email via its request.data fallback - see
        # axes.helpers.get_client_username. Covers wrong password, an
        # inactive account (ModelBackend's user_can_authenticate rejects
        # it), and an axes lockout with exactly the same generic error -
        # none of those states are distinguishable from the outside.
        user = authenticate(request=request, email=email, password=password)
        if user is None:
            return Response({"detail": LOGIN_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        django_login(request, user)
        request.session.cycle_key()
        return Response(MeSerializer(user).data)


class LogoutView(APIView):
    def post(self, request):
        django_logout(request)
        return Response({"detail": "Logged out."})


class LogoutAllView(APIView):
    """End every session for this user - PLAN.md B1.3's "log out everywhere".
    No password required: it only ever takes access away."""

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


class SecurityEventsView(APIView):
    """The caller's own recent security activity (logins, failed attempts,
    password/email changes...) so they can spot something they didn't do."""

    def get(self, request):
        events = request.user.security_events.order_by("-created_at")[:SECURITY_EVENTS_LIMIT]
        return Response(SecurityEventSerializer(events, many=True).data)


class OptionsView(APIView):
    """Choices for the profile form, so clients don't hard-code them.
    Public: nothing here is account-specific."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "currencies": [
                    {"value": value, "label": label} for value, label in Profile.Currency.choices
                ],
                "roles": [{"value": value, "label": label} for value, label in Profile.Role.choices],
                "timezones": sorted(available_timezones()),
            }
        )


class MeView(APIView):
    def get(self, request):
        return Response(MeSerializer(request.user).data)

    def patch(self, request):
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        if not user.check_password(serializer.validated_data["current_password"]):
            return Response({"detail": WRONG_PASSWORD_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        weak_password_response = _password_strength_error(serializer.validated_data["new_password"], user)
        if weak_password_response is not None:
            return weak_password_response
        user.set_password(serializer.validated_data["new_password"])
        user.password_changed_at = timezone.now()
        user.save()

        # Keep this session, end every other one.
        update_session_auth_hash(request, user)
        end_other_sessions(user, except_session_key=request.session.session_key)
        log_event("password_changed", request=request, user=user)

        return Response({"detail": "Password changed."})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle, PasswordResetAccountThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()

        user = User.objects.filter(email=email, is_active=True).first()
        if user:
            send_password_reset_email(user)
            log_event("password_reset_requested", request=request, user=user)

        return Response({"detail": RESET_MESSAGE})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = _decode_uid(data["uid"])
        if user is None or not default_token_generator.check_token(user, data["token"]):
            return Response({"detail": TOKEN_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        weak_password_response = _password_strength_error(data["new_password"], user)
        if weak_password_response is not None:
            return weak_password_response
        user.set_password(data["new_password"])
        user.password_changed_at = timezone.now()
        user.save()

        # No "current session" to protect - the caller isn't authenticated
        # on this endpoint.
        end_all_sessions(user)
        log_event("password_reset_done", request=request, user=user)

        return Response({"detail": "Password reset."})


class EmailChangeView(APIView):
    def post(self, request):
        serializer = EmailChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        new_email = serializer.validated_data["new_email"].lower()

        if not user.check_password(serializer.validated_data["current_password"]):
            return Response({"detail": WRONG_PASSWORD_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        if not User.objects.exclude(pk=user.pk).filter(email=new_email).exists():
            send_email_change_confirmation(user, new_email)

        # Same response whether or not the new address is available -
        # otherwise this endpoint could be used to probe other accounts'
        # emails, authenticated or not.
        return Response({"detail": EMAIL_CHANGE_MESSAGE})


class DeactivateView(APIView):
    def post(self, request):
        serializer = DeactivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        if not user.check_password(serializer.validated_data["current_password"]):
            return Response({"detail": WRONG_PASSWORD_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = False
        user.save()
        log_event("deactivated", request=request, user=user)

        end_all_sessions(user)
        django_logout(request)
        return Response({"detail": "Account deactivated."})
