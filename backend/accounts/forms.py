"""
Admin forms. UserCreationForm/UserChangeForm follow Django's own documented
recipe for a custom user model ("Custom users and django.contrib.admin") -
BaseUserCreationForm is the class Django's docs say to subclass for exactly
this.
"""

from django import forms
from django.contrib.auth.forms import BaseUserCreationForm
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm

from .models import Profile, User
from .validation import available_timezones

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
    # Plain CharField on the model (see models.py) - rendered as a proper
    # dropdown here instead of baking the full IANA zone list into choices
    # at the DB/migration level.
    timezone = forms.ChoiceField(choices=TIMEZONE_CHOICES)

    class Meta:
        model = Profile
        fields = ["display_name", "base_currency", "timezone"]
