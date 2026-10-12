from django import forms
from django.contrib.auth.forms import (
    AdminUserCreationForm,
    AuthenticationForm,
    UserChangeForm,
    UserCreationForm,
)

from .models import Address, User


class UniqueEmailMixin:
    """Lowercase the email and reject one another account already uses.

    The model's unique check compares the raw input, so ``Casey@Example.com``
    would slip past it and hit the database constraint instead.
    """

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        others = User.objects.exclude(pk=self.instance.pk)
        if others.filter(email=email).exists():
            raise forms.ValidationError("That email is already in use.")
        return email


class SignupForm(UniqueEmailMixin, UserCreationForm):
    """Django's stock signup fields plus a required, unique email.

    The email is what makes password reset possible. The widgets carry
    DaisyUI classes because plain Django forms own their own styling here.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class SignInForm(AuthenticationForm):
    """The stock authentication form, dressed in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class AdminAddUserForm(UniqueEmailMixin, AdminUserCreationForm):
    """The Django admin's "Add user" form, with the required email."""

    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class AdminChangeUserForm(UniqueEmailMixin, UserChangeForm):
    """The Django admin's user edit form, with the case-insensitive email check."""

    class Meta(UserChangeForm.Meta):
        model = User


class AddressForm(forms.ModelForm):
    """Add or edit an address-book entry.

    Validation comes from the model fields (state choices, ZIP validator);
    defaults are set with their own buttons, not here.
    """

    class Meta:
        model = Address
        fields = Address.FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            else:
                widget.attrs["class"] = "input w-full"
