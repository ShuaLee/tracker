from django.contrib.auth import get_user_model
from rest_framework import serializers

from .entitlements import plan_for
from .models import Profile, SecurityEvent
from .validators import validate_user_password

User = get_user_model()


# --- me ----------------------------------------------------------------------


class ProfileSerializer(serializers.ModelSerializer):
    # timezone is checked by the model field's validate_timezone, which
    # ModelSerializer picks up automatically.
    class Meta:
        model = Profile
        fields = ["display_name", "base_currency", "timezone"]


class MeSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    is_email_verified = serializers.BooleanField(read_only=True)
    plan = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["email", "is_email_verified", "date_joined", "plan", "profile"]
        read_only_fields = ["email", "date_joined"]

    def get_plan(self, user):
        # Read-only: plans are set in admin (later, by billing).
        plan = plan_for(user)
        return {"slug": plan.slug, "name": plan.name}

    def update(self, instance, validated_data):
        # Only the profile is writable here. Email has its own confirmed
        # flow (email/change/); the password has password/change/.
        profile_data = validated_data.pop("profile", None)
        if profile_data:
            profile = instance.profile
            for field, value in profile_data.items():
                setattr(profile, field, value)
            profile.save()
        return instance


# --- registration and email verification ------------------------------------


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    display_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        # An unsaved stand-in lets the similarity validator compare the
        # password with this email and display name before the user exists.
        validate_user_password(attrs["password"], User(email=attrs["email"].lower()), attrs["display_name"])
        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.CharField()
    email = serializers.EmailField()
    token = serializers.CharField()


class EmailSerializer(serializers.Serializer):
    """Just an email: resend verification, request a password reset."""

    email = serializers.EmailField()


# --- sessions ----------------------------------------------------------------


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class LogoutAllSerializer(serializers.Serializer):
    # False: end every session, this one included ("someone else is in my
    # account"). True: keep this device signed in.
    keep_current = serializers.BooleanField(default=False)


# --- password, email, deletion ----------------------------------------------


class CurrentPasswordSerializer(serializers.Serializer):
    """Re-authentication for sensitive actions (delete account)."""

    current_password = serializers.CharField(write_only=True, trim_whitespace=False)


class ChangePasswordSerializer(CurrentPasswordSerializer):
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value):
        validate_user_password(value, self.context["request"].user)
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class ChangeEmailSerializer(CurrentPasswordSerializer):
    new_email = serializers.EmailField()


# --- security activity -------------------------------------------------------


class SecurityEventSerializer(serializers.ModelSerializer):
    event_label = serializers.CharField(source="get_event_display", read_only=True)

    class Meta:
        model = SecurityEvent
        fields = ["event", "event_label", "ip", "user_agent", "created_at"]
        read_only_fields = fields
