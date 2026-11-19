"""Admin forms, following Django's documented recipe for a custom user model
("Custom users and django.contrib.admin")."""

from django import forms
from django.contrib.auth.forms import BaseUserCreationForm
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm

from .models import Profile, User
from .validators import available_timezones

TIMEZONE_CHOICES = [(tz, tz) for tz in sorted(available_timezones())]


class UserCreationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email",)
        field_classes = {}


class UserChangeForm(DjangoUserChangeForm):
    class Meta(DjangoUserChangeForm.Meta):
        model = User
        fields = "__all__"
        field_classes = {}


class ProfileInlineForm(forms.ModelForm):
    # The model field is a plain CharField; show the IANA list as a dropdown.
    timezone = forms.ChoiceField(choices=TIMEZONE_CHOICES)

    class Meta:
        model = Profile
        fields = ["display_name", "base_currency", "timezone"]
