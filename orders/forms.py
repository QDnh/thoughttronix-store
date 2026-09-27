"""The checkout form — the codebase's showcase of declarative validation.

Every rule is visible at its field declaration, in the style of data
annotations: field types validate (``EmailField``), field arguments
validate (``required``, ``max_length``, ``ChoiceField``), and the
``validators=[...]`` list carries the rest. No ``clean_*`` methods
and no ``clean()`` — none of its current rules need imperative validation.
"""

from django import forms
from django.core.validators import RegexValidator

from accounts.validators import US_STATES, zip_validator
from products.forms import StyledModelForm

from .models import DiscountCode, Order, normalize_code
from .validators import validate_card_number, validate_expiry

cvv_validator = RegexValidator(r"^\d{3,4}$", "Enter the 3- or 4-digit CVV.")


class CheckoutForm(forms.Form):
    """One page, one POST: contact, shipping, billing, payment."""

    email = forms.EmailField(label="Email")

    shipping_name = forms.CharField(label="Full name", max_length=100)
    shipping_street = forms.CharField(label="Street address", max_length=200)
    shipping_line2 = forms.CharField(
        label="Apt, suite, etc. (optional)", max_length=200, required=False
    )
    shipping_city = forms.CharField(label="City", max_length=100)
    shipping_state = forms.ChoiceField(label="State", choices=US_STATES)
    shipping_zip = forms.CharField(
        label="ZIP code", max_length=10, validators=[zip_validator]
    )

    billing_name = forms.CharField(label="Full name", max_length=100)
    billing_street = forms.CharField(label="Street address", max_length=200)
    billing_line2 = forms.CharField(
        label="Apt, suite, etc. (optional)", max_length=200, required=False
    )
    billing_city = forms.CharField(label="City", max_length=100)
    billing_state = forms.ChoiceField(label="State", choices=US_STATES)
    billing_zip = forms.CharField(
        label="ZIP code", max_length=10, validators=[zip_validator]
    )

    card_number = forms.CharField(
        label="Card number", max_length=23, validators=[validate_card_number]
    )
    card_expiry = forms.CharField(
        label="Expiry (MM/YY)", max_length=5, validators=[validate_expiry]
    )
    card_cvv = forms.CharField(label="CVV", max_length=4, validators=[cvv_validator])

    # Address-book opt-ins; the view saves after the order is placed.
    save_shipping = forms.BooleanField(
        label="Save this address to my account", required=False
    )
    save_billing = forms.BooleanField(
        label="Save this address to my account", required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "checkbox checkbox-sm"
            else:
                widget.attrs["class"] = "input w-full"

    # Field groups for the template — the form owns its own structure.

    def shipping_fields(self):
        return [self[name] for name in self.fields if name.startswith("shipping_")]

    def billing_fields(self):
        return [self[name] for name in self.fields if name.startswith("billing_")]

    def card_fields(self):
        return [self[name] for name in self.fields if name.startswith("card_")]


class DiscountEntryForm(forms.Form):
    """The checkout's discount-code box, validated against one cart.

    Kept apart from ``CheckoutForm`` so that form stays purely declarative:
    whether a code is usable depends on the clock and the cart, which no
    field declaration can express. Its input sits outside the checkout
    ``<form>`` element but joins it via the HTML ``form`` attribute, so
    the Apply button and Place order both submit it. A blank box means no
    discount; ``cleaned_data["discount_code"]`` is a ``DiscountCode`` or
    ``None``.
    """

    discount_code = forms.CharField(
        label="Discount code",
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={
                "form": "checkout-form",
                "class": "input join-item w-full uppercase",
                "placeholder": "e.g. SPRING20",
                "autocomplete": "off",
            }
        ),
    )

    def __init__(self, *args, cart, **kwargs):
        super().__init__(*args, **kwargs)
        self.cart = cart

    def clean_discount_code(self):
        text = self.cleaned_data["discount_code"].strip()
        if not text:
            return None
        return DiscountCode.objects.for_checkout(
            text, [line.product for line in self.cart.lines()]
        )


class DiscountCodeForm(StyledModelForm):
    """Back-office create/edit for a discount code.

    The model's ``clean()`` checks the date window; the product rule lives
    here because a many-to-many can't be read on an unsaved instance.
    """

    class Meta:
        model = DiscountCode
        fields = [
            "code",
            "percent_off",
            "applies_to",
            "products",
            "starts_at",
            "expires_at",
        ]
        help_texts = {
            "products": "Only for “Specific products”. Hold Ctrl (⌘ on Mac) to pick several.",
            "starts_at": "Leave as now to start immediately.",
        }
        widgets = {
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "expires_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def clean_code(self):
        return normalize_code(self.cleaned_data["code"])

    def clean(self):
        cleaned = super().clean()
        applies_to = cleaned.get("applies_to")
        products = cleaned.get("products")
        if applies_to == DiscountCode.AppliesTo.PRODUCTS and not products:
            self.add_error("products", "Pick at least one product.")
        elif applies_to == DiscountCode.AppliesTo.ORDER and products:
            self.add_error(
                "products",
                "An entire-order code can't be limited to products — "
                "clear the selection or choose “Specific products”.",
            )
        return cleaned


class OrderStatusForm(forms.ModelForm):
    """The back-office status dropdown — any of the four states, anytime.

    Guarding the workflow (no un-cancelling, no re-shipping a delivered
    order) is deliberately left as a student exercise.
    """

    class Meta:
        model = Order
        fields = ["status"]
        widgets = {"status": forms.Select(attrs={"class": "select"})}
