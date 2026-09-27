"""Order placement — one of the codebase's two deliberate deep modules.

The interface is the product: one function that turns a cart and a
validated checkout into an order, all-or-nothing. Callers never touch
``Order`` construction directly. ``quote`` prices a cart under a discount
code with the same arithmetic ``place_order`` uses, so what the checkout
page previews is exactly what the order records.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from .models import Cart, CartItem, DiscountCode, Order, OrderItem

ADDRESS_FIELDS = [
    "email",
    "shipping_name",
    "shipping_street",
    "shipping_line2",
    "shipping_city",
    "shipping_state",
    "shipping_zip",
    "billing_name",
    "billing_street",
    "billing_line2",
    "billing_city",
    "billing_state",
    "billing_zip",
]


@dataclass(frozen=True)
class PricedLine:
    """One cart line with its discount worked out."""

    item: CartItem
    discount: Decimal

    @property
    def total(self) -> Decimal:
        return self.item.line_total - self.discount


@dataclass(frozen=True)
class Quote:
    """A cart priced under at most one discount code.

    The order discount is the sum of the rounded line discounts, so every
    number on a receipt adds up exactly.
    """

    lines: list[PricedLine]
    code: DiscountCode | None

    @property
    def subtotal(self) -> Decimal:
        return sum((line.item.line_total for line in self.lines), Decimal("0.00"))

    @property
    def discount(self) -> Decimal:
        return sum((line.discount for line in self.lines), Decimal("0.00"))

    @property
    def total(self) -> Decimal:
        return self.subtotal - self.discount


def _price(items: Iterable[CartItem], code: DiscountCode | None) -> Quote:
    lines = [
        PricedLine(
            item=item,
            discount=(
                code.discount_for(item.product, item.line_total)
                if code
                else Decimal("0.00")
            ),
        )
        for item in items
    ]
    return Quote(lines=lines, code=code)


def quote(cart: Cart, code: DiscountCode | None = None) -> Quote:
    """Price the cart's lines under ``code`` (``None`` means full price).

    Does not check whether the code is currently valid — that is
    ``DiscountCode.objects.for_checkout``'s job.
    """
    return _price(cart.lines(), code)


@transaction.atomic
def place_order(
    cart: Cart,
    user: AbstractBaseUser,
    checkout_data: Mapping[str, Any],
    *,
    coupon_code: str | None = None,
) -> Order:
    """Create an order from the cart's contents, then empty the cart.

    ``checkout_data`` is the ``cleaned_data`` of a valid ``CheckoutForm``.
    Addresses and line prices are denormalized onto the order — an order
    is a snapshot, immune to later catalog or address edits. Of the card,
    only the last four digits are stored; the full number and CVV never
    touch the database.

    ``coupon_code`` is the discount code the customer typed, if any. It is
    checked again here, inside the transaction — it may have expired since
    the checkout form accepted it. Each line's discount and the code's
    text and percent are snapshotted, so later edits to the code (or its
    expiry) never change this order.

    All-or-nothing: runs in a transaction, so a failure partway through
    leaves no partial order and the cart intact.

    Raises ``ValueError`` if the cart is empty or holds a product that is
    no longer available, and ``ValidationError`` (with the customer-facing
    message) if ``coupon_code`` can't be used on this cart right now.
    """
    lines = list(cart.lines())
    if not lines:
        raise ValueError("Cannot place an order from an empty cart.")
    unavailable = [line.product.name for line in lines if not line.product.is_available]
    if unavailable:
        raise ValueError(
            f"No longer available: {', '.join(unavailable)}. "
            "Remove them from the cart to check out."
        )

    code = None
    if coupon_code:
        code = DiscountCode.objects.for_checkout(
            coupon_code, [line.product for line in lines]
        )
    priced = _price(lines, code)

    card_digits = checkout_data["card_number"].replace(" ", "").replace("-", "")
    order = Order.objects.create(
        user=user,
        subtotal=priced.subtotal,
        discount_amount=priced.discount,
        total=priced.total,
        discount_code=code,
        discount_code_text=code.code if code else "",
        discount_percent=code.percent_off if code else None,
        card_last4=card_digits[-4:],
        **{name: checkout_data[name] for name in ADDRESS_FIELDS},
    )
    for line in priced.lines:
        OrderItem.objects.create(
            order=order,
            product=line.item.product,
            product_name=line.item.product.name,
            unit_price=line.item.product.price,
            quantity=line.item.quantity,
            discount_amount=line.discount,
        )
    cart.items.all().delete()
    return order
