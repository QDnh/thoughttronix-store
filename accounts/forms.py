from django import forms
from django.contrib.auth.forms import (
    AdminUserCreationForm,
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
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


class ChangeEmailForm(forms.Form):
    """A new email, confirmed with the signed-in user's current password.

    The password check stops someone at an unattended, signed-in session
    from redirecting the account's recovery to an inbox they control.
    """

    email = forms.EmailField(label="New email")
    password = forms.CharField(
        label="Current password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if email == self.user.email:
            raise forms.ValidationError("That is already your email.")
        if User.objects.exclude(pk=self.user.pk).filter(email=email).exists():
            raise forms.ValidationError("That email is already in use.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Your password was entered incorrectly.")
        return password


class StyledPasswordChangeForm(PasswordChangeForm):
    """The stock change-password form (old password, new one twice), in DaisyUI.

    Validation is all Django's: the old password is checked and the new
    one runs through ``AUTH_PASSWORD_VALIDATORS``, the same as signup.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class StyledPasswordResetForm(PasswordResetForm):
    """The stock reset-request form (just an email), in DaisyUI.

    Django's lookup ignores case, skips accounts with unusable passwords,
    and never says whether the email matched, so the page can't be used
    to find out who has an account.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class StyledSetPasswordForm(SetPasswordForm):
    """The stock reset-confirm form (new password twice, no old one), in DaisyUI.

    The new password runs through ``AUTH_PASSWORD_VALIDATORS``, the same
    as signup, so a reset can't leave the account with a weak password.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


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
