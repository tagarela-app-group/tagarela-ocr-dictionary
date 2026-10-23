from django import forms
from django.contrib.auth.forms import BaseUserCreationForm
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm

from apps.accounts.models import User


class SignupForm(forms.Form):
    name = forms.CharField(max_length=150)

    def signup(self, request, user: User) -> None:
        user.name = self.cleaned_data["name"].strip()
        user.save(update_fields=["name"])


class UserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "name")


class UserChangeForm(BaseUserChangeForm):
    class Meta:
        model = User
        fields = ("email", "name")
