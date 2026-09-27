"""Cart and checkout views — thin per the architecture convention.

The three HTMX interactions of the core live here: add-to-cart, quantity
change, and line removal. Each renders a partial (never ``base.html``);
the responses carry the navbar badge as an out-of-band swap via the
``oob_badge`` context flag. Checkout is conventional full-page work:
validate the form, hand everything to ``place_order``.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.mixins import StaffRequiredMixin
from accounts.models import Address
from products.models import Product

from .forms import CheckoutForm, DiscountCodeForm, DiscountEntryForm, OrderStatusForm
from .models import Cart, CartItem, DiscountCode, Order
from .services import place_order, quote


class CartView(LoginRequiredMixin, TemplateView):
    """The customer's cart page."""

    template_name = "orders/cart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cart"] = Cart.for_user(self.request.user)
        return context


class AddToCartView(LoginRequiredMixin, View):
    """HTMX: add a product; the button swaps and the badge updates OOB.

    Looks the product up through ``available()``, so adding an
    unavailable product 404s — the same not-for-sale semantics as the
    public catalog.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product.objects.available(), pk=pk)
        item = Cart.for_user(request.user).add(product)
        return render(
            request,
            "orders/partials/_add_button.html",
            {"product": product, "in_cart": item.quantity, "oob_badge": True},
        )


class CartItemActionView(LoginRequiredMixin, View):
    """Base for HTMX line mutations: act, then re-render the cart contents.

    Items are always fetched through the owner's cart — never by bare pk.
    """

    def post(self, request, pk):
        item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        self.act(item)
        return render(
            request,
            "orders/partials/_cart_contents.html",
            {"cart": item.cart, "oob_badge": True},
        )

    def act(self, item):
        raise NotImplementedError


class IncrementCartItemView(CartItemActionView):
    def act(self, item):
        item.increment()


class DecrementCartItemView(CartItemActionView):
    def act(self, item):
        item.decrement()


class RemoveCartItemView(CartItemActionView):
    def act(self, item):
        item.delete()


def checkout_summary_context(cart, discount_form):
    """What ``_checkout_summary.html`` needs: the cart priced under the code.

    An unbound or invalid discount form prices the cart at full price —
    a rejected code never discounts anything.
    """
    code = None
    if discount_form.is_bound and discount_form.is_valid():
        code = discount_form.cleaned_data["discount_code"]
    return {"cart": cart, "discount_form": discount_form, "quote": quote(cart, code)}


class CheckoutView(LoginRequiredMixin, FormView):
    """The single checkout page: validate the form, hand off to the service.

    A cart that can't check out (empty, or holding a product that has
    since become unavailable) is sent back to the cart page to be fixed —
    ``place_order`` enforces the same rules transactionally as the
    backstop.
    """

    template_name = "orders/checkout.html"
    form_class = CheckoutForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        cart = self.cart = Cart.for_user(request.user)
        if not cart.items.exists():
            messages.info(request, "Your cart is empty — add something first.")
            return redirect("orders:cart")
        unavailable = [
            line.product.name for line in cart.lines() if not line.product.is_available
        ]
        if unavailable:
            messages.warning(
                request,
                f"No longer available: {', '.join(unavailable)}. "
                "Remove them from the cart to check out.",
            )
            return redirect("orders:cart")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Pre-fill each address section from the customer's defaults."""
        initial = super().get_initial()
        for address in self.request.user.addresses.all():
            if address.is_default_shipping:
                initial.update(address.as_checkout_initial("shipping_"))
            if address.is_default_billing:
                initial.update(address.as_checkout_initial("billing_"))
        return initial

    def post(self, request, *args, **kwargs):
        """Both forms must pass: the checkout itself and the discount box."""
        form = self.get_form()
        self.discount_form = DiscountEntryForm(request.POST, cart=self.cart)
        if all([form.is_valid(), self.discount_form.is_valid()]):
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        discount_form = getattr(self, "discount_form", None) or DiscountEntryForm(
            cart=self.cart
        )
        context.update(checkout_summary_context(self.cart, discount_form))
        context["addresses"] = self.request.user.addresses.all()
        return context

    def form_valid(self, form):
        user = self.request.user
        code = self.discount_form.cleaned_data["discount_code"]
        try:
            order = place_order(
                self.cart,
                user,
                form.cleaned_data,
                coupon_code=code.code if code else None,
            )
        except ValidationError as error:
            # The code went stale between form validation and placement.
            self.discount_form.add_error("discount_code", error)
            return self.form_invalid(form)
        # Only after the order succeeds — a failed checkout saves nothing.
        if form.cleaned_data["save_shipping"]:
            Address.objects.save_from_checkout(
                user, form.cleaned_data, prefix="shipping_"
            )
        if form.cleaned_data["save_billing"]:
            Address.objects.save_from_checkout(
                user, form.cleaned_data, prefix="billing_"
            )
        messages.success(self.request, f"Order {order.number} placed. Thank you!")
        return redirect(reverse("orders:confirmation", kwargs={"pk": order.pk}))


class ApplyDiscountView(LoginRequiredMixin, View):
    """HTMX: preview a discount code in the checkout's order summary.

    Re-renders the summary with the discount lines and new total, or with
    the code's error; the Place order button's total updates OOB. Nothing
    is saved — the code is checked again when the order is placed. A
    blank code clears any discount.
    """

    def post(self, request):
        cart = Cart.for_user(request.user)
        discount_form = DiscountEntryForm(request.POST, cart=cart)
        context = checkout_summary_context(cart, discount_form)
        context["oob_total"] = True
        return render(request, "orders/partials/_checkout_summary.html", context)


class CheckoutAddressFieldsView(LoginRequiredMixin, View):
    """HTMX: refill one checkout address section from a saved address.

    ``?address=<pk>`` picks the address (always through the owner); an
    empty value returns blank fields for typing a new one. Only text boxes
    change — the checkout POST and its validation are untouched.
    """

    def get(self, request, section):
        if section not in ("shipping", "billing"):
            raise Http404
        prefix = f"{section}_"
        pk = request.GET.get("address", "")
        initial = {}
        if pk:
            if not pk.isdigit():
                raise Http404
            address = get_object_or_404(Address, pk=pk, user=request.user)
            initial = address.as_checkout_initial(prefix)
        form = CheckoutForm(initial=initial)
        fields = [form[name] for name in form.fields if name.startswith(prefix)]
        return render(
            request, "orders/partials/_address_fields.html", {"fields": fields}
        )


class OwnOrdersMixin(LoginRequiredMixin):
    """Orders are always fetched through the owner — never by bare pk."""

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderConfirmationView(OwnOrdersMixin, DetailView):
    template_name = "orders/confirmation.html"
    context_object_name = "order"


class OrderHistoryView(OwnOrdersMixin, ListView):
    """The customer's orders, most recent first per the model ordering."""

    template_name = "orders/order_history.html"
    context_object_name = "orders"


class OrderDetailView(OwnOrdersMixin, DetailView):
    template_name = "orders/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("items")


# --- The back office --------------------------------------------------------
#
# Staff-only order oversight: every customer's orders, filterable by
# status, with the status dropdown on the detail page. The ``section``
# context entry drives the active tab in the staff shell.


class ManageOrderListView(StaffRequiredMixin, ListView):
    """All orders, most recent first, filterable via ``?status=``."""

    template_name = "orders/manage_orders.html"
    context_object_name = "orders"
    paginate_by = 20
    extra_context = {"section": "orders"}

    def get_queryset(self):
        orders = Order.objects.select_related("user")
        status = self.request.GET.get("status", "")
        if status in Order.Status.values:
            orders = orders.filter(status=status)
        return orders

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Order.Status.choices
        context["active_status"] = self.request.GET.get("status", "")
        return context


class ManageOrderDetailView(StaffRequiredMixin, DetailView):
    """Any order's detail, with the status form alongside."""

    template_name = "orders/manage_order_detail.html"
    context_object_name = "order"
    queryset = Order.objects.select_related("user").prefetch_related("items")
    extra_context = {"section": "orders"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_form"] = OrderStatusForm(instance=self.object)
        return context


class UpdateOrderStatusView(StaffRequiredMixin, View):
    """POST-only: set an order's status from the back-office dropdown."""

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"{order.number} is now {order.get_status_display().lower()}.",
            )
        else:
            messages.error(request, "That isn't a status an order can have.")
        return redirect("orders:manage_order_detail", pk=order.pk)


# Discount codes: marketing creates and retires them here, no engineering
# ticket required. Codes are ended rather than deleted once any order has
# used one, so the usage history survives.


class ManageDiscountListView(StaffRequiredMixin, ListView):
    """Every code with its status and usage, filterable via ``?status=``."""

    template_name = "orders/manage_discounts.html"
    context_object_name = "codes"
    extra_context = {"section": "discounts"}

    def get_queryset(self):
        codes = DiscountCode.objects.with_order_count().prefetch_related("products")
        status = self.request.GET.get("status", "")
        if status in DiscountCode.Status.values:
            # Each status value names its queryset method: .active(), etc.
            codes = getattr(codes, status)()
        return codes

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = DiscountCode.Status.choices
        context["active_status"] = self.request.GET.get("status", "")
        return context


class ManageDiscountCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = DiscountCode
    form_class = DiscountCodeForm
    template_name = "orders/manage_discount_form.html"
    success_url = reverse_lazy("orders:manage_discounts")
    success_message = "%(code)s created."
    extra_context = {"section": "discounts"}


class ManageDiscountUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DiscountCode
    form_class = DiscountCodeForm
    template_name = "orders/manage_discount_form.html"
    success_url = reverse_lazy("orders:manage_discounts")
    success_message = "%(code)s saved."
    extra_context = {"section": "discounts"}


class EndDiscountView(StaffRequiredMixin, View):
    """POST-only: retire a code immediately; past orders are untouched."""

    def post(self, request, pk):
        code = get_object_or_404(DiscountCode, pk=pk)
        code.end_now()
        messages.success(request, f"{code.code} has ended.")
        return redirect("orders:manage_discounts")


class ManageDiscountDeleteView(StaffRequiredMixin, SuccessMessageMixin, DeleteView):
    """Delete a code no order has used — for fixing mistakes, not retiring.

    Used codes 404 here; they are ended instead, keeping their history.
    """

    queryset = DiscountCode.objects.filter(orders__isnull=True)
    context_object_name = "code"
    template_name = "orders/manage_discount_confirm_delete.html"
    success_url = reverse_lazy("orders:manage_discounts")
    success_message = "Code deleted."
    extra_context = {"section": "discounts"}
