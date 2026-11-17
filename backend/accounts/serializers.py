from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Profile
from .validation import validate_user_password

User = get_user_model()


# ---------------------------------------------------------------------------
# me/
# ---------------------------------------------------------------------------


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["display_name", "base_currency", "timezone", "role"]


class MeSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    is_email_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ["email", "is_email_verified", "date_joined", "profile"]
        read_only_fields = ["email", "is_email_verified", "date_joined"]

    def update(self, instance, validated_data):
        # Only Profile fields are ever writable here - email isn't changed
        # on this endpoint (PLAN.md), and there's no password field to begin
        # with.
        profile_data = validated_data.pop("profile", None)
        if profile_data:
            profile = instance.profile
            for field, value in profile_data.items():
                setattr(profile, field, value)
            profile.save()
        return instance


# ---------------------------------------------------------------------------
# register / verify / resend
# ---------------------------------------------------------------------------


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    display_name = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        # Validated against an unsaved stand-in so UserAttributeSimilarityValidator
        # can compare the password to this email/display_name even though
        # the account doesn't exist yet.
        stub = User(email=attrs["email"].lower())
        validate_user_password(attrs["password"], stub, display_name=attrs["display_name"])
        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.CharField()
    email = serializers.EmailField()
    token = serializers.CharField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


# ---------------------------------------------------------------------------
# password
# ---------------------------------------------------------------------------


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)


# ---------------------------------------------------------------------------
# email change / deactivate
# ---------------------------------------------------------------------------


class EmailChangeSerializer(serializers.Serializer):
    new_email = serializers.EmailField()
    current_password = serializers.CharField(write_only=True)


class DeactivateSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
