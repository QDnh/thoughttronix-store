from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    AddressForm,
    ChangeEmailForm,
    SignInForm,
    SignupForm,
    StyledPasswordChangeForm,
)
from .models import Address


class SignupView(SuccessMessageMixin, CreateView):
    """Create a customer account, then hand off to the login page.

    New users sign in themselves — auto-login after signup is left as a
    student exercise.
    """

    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")
    success_message = "Account created — you can now sign in."


class SignInView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = SignInForm


class SignOutView(LogoutView):
    def post(self, request, *args, **kwargs):
        # Flash after super() has flushed the session, or the message
        # would be wiped along with it.
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have signed out.")
        return response


# --- The Security Center ----------------------------------------------------


class SecurityView(LoginRequiredMixin, TemplateView):
    """The hub: the signed-in user's username and email, with links to change
    them. Every account holder gets the same page — no role checks."""

    template_name = "accounts/security.html"


class ChangeEmailView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    """Change email with the current password; the old address gets a notice."""

    form_class = ChangeEmailForm
    template_name = "accounts/change_email.html"
    success_url = reverse_lazy("accounts:security")
    success_message = "Email updated."

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def form_valid(self, form):
        self.request.user.change_email(form.cleaned_data["email"])
        return super().form_valid(form)


class ChangePasswordView(LoginRequiredMixin, SuccessMessageMixin, PasswordChangeView):
    """Change password with the old one; the account's email gets a notice.

    Django's session handling is kept as-is: this session stays signed in
    and every other session for the account is signed out.
    """

    form_class = StyledPasswordChangeForm
    template_name = "accounts/change_password.html"
    success_url = reverse_lazy("accounts:security")
    success_message = "Password updated."

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.user.notify_password_changed()
        return response


# --- The address book -------------------------------------------------------


class OwnAddressesMixin(LoginRequiredMixin):
    """Addresses are always fetched through the owner — never by bare pk."""

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressListView(OwnAddressesMixin, ListView):
    template_name = "accounts/address_list.html"
    context_object_name = "addresses"

    def get_queryset(self):
        return super().get_queryset().order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        addresses = context["addresses"]
        context["has_default_shipping"] = any(a.is_default_shipping for a in addresses)
        context["has_default_billing"] = any(a.is_default_billing for a in addresses)
        return context


class AddressCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    form_class = AddressForm
    template_name = "accounts/address_form.html"
    success_url = reverse_lazy("accounts:addresses")
    success_message = "Address saved."

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class AddressUpdateView(OwnAddressesMixin, SuccessMessageMixin, UpdateView):
    form_class = AddressForm
    template_name = "accounts/address_form.html"
    success_url = reverse_lazy("accounts:addresses")
    success_message = "Address updated."


class AddressDeleteView(OwnAddressesMixin, SuccessMessageMixin, DeleteView):
    """Delete with a confirmation page; a deleted default leaves its slot empty."""

    template_name = "accounts/address_confirm_delete.html"
    success_url = reverse_lazy("accounts:addresses")
    success_message = "Address deleted."


class MakeDefaultAddressView(LoginRequiredMixin, View):
    """POST-only base: make an address a default, then back to the list."""

    kind = ""  # "shipping" or "billing"

    def post(self, request, pk):
        address = get_object_or_404(Address, pk=pk, user=request.user)
        getattr(address, f"make_default_{self.kind}")()
        messages.success(request, f"Default {self.kind} address updated.")
        return redirect("accounts:addresses")


class MakeDefaultShippingView(MakeDefaultAddressView):
    kind = "shipping"


class MakeDefaultBillingView(MakeDefaultAddressView):
    kind = "billing"
