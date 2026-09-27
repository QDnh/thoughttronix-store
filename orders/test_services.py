"""place_order tests — coverage priority 3 in the PRD.

Denormalization, cart emptying, atomicity, unavailable rejection, the
card_last4-only rule, and discount codes: the per-line math and the
snapshot that keeps placed orders immune to later code changes.
"""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from products.models import Product

from .models import CartItem, Order, OrderItem
from .services import place_order
from .test_checkout_form import VALID_DATA


@pytest.fixture
def checkout_data():
    return dict(VALID_DATA)


def test_creates_an_order_with_denormalized_snapshot(cart, cart_item, checkout_data):
    order = place_order(cart, cart.user, checkout_data)

    assert order.user == cart.user
    assert order.total == Decimal("699.98")
    assert order.status == Order.Status.PLACED
    item = order.items.get()
    assert item.product_name == "Seraphine Home Hub"
    assert item.unit_price == Decimal("349.99")
    assert item.quantity == 2
    assert item.line_total == Decimal("699.98")


def test_order_history_survives_catalog_changes(cart, cart_item, checkout_data):
    order = place_order(cart, cart.user, checkout_data)

    product = cart_item.product
    product.name = "Seraphine Home Hub II"
    product.price = Decimal("999.00")
    product.save()

    item = order.items.get()
    assert item.product_name == "Seraphine Home Hub"
    assert item.unit_price == Decimal("349.99")


def test_addresses_and_email_are_copied_onto_the_order(cart, cart_item, checkout_data):
    order = place_order(cart, cart.user, checkout_data)

    assert order.email == "casey@example.com"
    assert order.shipping_street == "12 Cortex Lane"
    assert order.shipping_line2 == "Unit 7"
    assert order.shipping_state == "TX"
    assert order.billing_zip == "79015-1234"


def test_only_the_last_four_card_digits_are_stored(cart, cart_item, checkout_data):
    order = place_order(cart, cart.user, checkout_data)

    assert order.card_last4 == "4242"
    stored = [field.name for field in Order._meta.get_fields()]
    assert "card_number" not in stored
    assert "card_cvv" not in stored
    assert "card_expiry" not in stored


def test_the_cart_is_emptied(cart, cart_item, checkout_data):
    place_order(cart, cart.user, checkout_data)

    assert not cart.items.exists()
    assert cart.total() == Decimal("0.00")


def test_an_empty_cart_is_rejected(cart, checkout_data):
    with pytest.raises(ValueError):
        place_order(cart, cart.user, checkout_data)

    assert not Order.objects.exists()


def test_an_unavailable_product_is_rejected(
    cart, cart_item, unavailable_product, checkout_data
):
    cart.items.create(product=unavailable_product)

    with pytest.raises(ValueError, match="EchoPatch"):
        place_order(cart, cart.user, checkout_data)

    assert not Order.objects.exists()
    assert cart.items.count() == 2  # the cart is untouched


def test_a_failure_midway_leaves_no_partial_order(
    cart, cart_item, category, checkout_data, monkeypatch
):
    """All-or-nothing: if any line fails, no order and no emptied cart."""
    cart.add(
        Product.objects.create(
            name="Charging Pillow",
            slug="charging-pillow",
            price=Decimal("69.00"),
            category=category,
        )
    )

    original = OrderItem.objects.create
    calls = {"count": 0}

    def create_then_explode(**kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("boom")
        return original(**kwargs)

    monkeypatch.setattr(OrderItem.objects, "create", create_then_explode)

    with pytest.raises(RuntimeError):
        place_order(cart, cart.user, checkout_data)

    assert not Order.objects.exists()
    assert not OrderItem.objects.exists()
    assert CartItem.objects.count() == 2


# --- Discount codes ------------------------------------------------------------


@pytest.fixture
def pillow(category):
    return Product.objects.create(
        name="Charging Pillow",
        slug="charging-pillow",
        price=Decimal("69.00"),
        category=category,
    )


def test_no_code_means_subtotal_equals_total(cart, cart_item, checkout_data):
    order = place_order(cart, cart.user, checkout_data)

    assert order.subtotal == order.total == Decimal("699.98")
    assert order.discount_amount == Decimal("0.00")
    assert order.discount_code is None
    assert order.discount_code_text == ""


def test_an_order_wide_code_discounts_every_line(
    cart, cart_item, pillow, order_code, checkout_data
):
    cart.add(pillow)

    order = place_order(cart, cart.user, checkout_data, coupon_code="THOUGHTS15")

    # 15% of 699.98 = 104.997 → 105.00; 15% of 69.00 = 10.35.
    hub, pillow_line = order.items.all()
    assert hub.discount_amount == Decimal("105.00")
    assert pillow_line.discount_amount == Decimal("10.35")
    assert order.subtotal == Decimal("768.98")
    assert order.discount_amount == Decimal("115.35")
    assert order.total == Decimal("653.63")


def test_a_product_code_discounts_only_its_products(
    cart, cart_item, pillow, seraphine_code, checkout_data
):
    cart.add(pillow)

    order = place_order(cart, cart.user, checkout_data, coupon_code="SERAPHINE50")

    hub, pillow_line = order.items.all()
    assert hub.discount_amount == Decimal("349.99")
    assert hub.charged == Decimal("349.99")
    assert pillow_line.discount_amount == Decimal("0.00")
    assert order.total == Decimal("418.99")


def test_the_order_discount_is_the_sum_of_rounded_lines(
    cart, category, order_code, checkout_data
):
    """Round each line, then add — never round the subtotal."""
    for slug, price in [("a", "0.10"), ("b", "0.10"), ("c", "0.10")]:
        cart.add(
            Product.objects.create(
                name=slug, slug=slug, price=Decimal(price), category=category
            )
        )

    order = place_order(cart, cart.user, checkout_data, coupon_code="THOUGHTS15")

    # Each line: 15% of 0.10 = 0.015 → 0.02 (half-up). 3 × 0.02 = 0.06,
    # where 15% of the 0.30 subtotal would have been 0.045 → 0.05.
    assert order.discount_amount == Decimal("0.06")
    assert sum(item.discount_amount for item in order.items.all()) == Decimal("0.06")


def test_the_code_is_snapshotted_onto_the_order(
    cart, cart_item, order_code, checkout_data
):
    order = place_order(cart, cart.user, checkout_data, coupon_code=" thoughts15 ")

    assert order.discount_code == order_code
    assert order.discount_code_text == "THOUGHTS15"
    assert order.discount_percent == 15


def test_ending_editing_or_deleting_a_code_never_changes_placed_orders(
    cart, cart_item, order_code, checkout_data
):
    order = place_order(cart, cart.user, checkout_data, coupon_code="THOUGHTS15")

    order_code.end_now()
    order_code.percent_off = 90
    order_code.save()
    order_code.delete()

    order.refresh_from_db()
    assert order.discount_code is None  # the link goes; the snapshot stays
    assert order.discount_code_text == "THOUGHTS15"
    assert order.discount_percent == 15
    assert order.discount_amount == Decimal("105.00")
    assert order.total == Decimal("594.98")
    assert order.items.get().discount_amount == Decimal("105.00")


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("NOPE", "We don't recognize that code."),
        ("SPRING20", "This code expired on"),
        ("HOLIDAY25", "This code isn't active until"),
    ],
)
def test_an_unusable_code_places_nothing(
    cart, cart_item, expired_code, scheduled_code, checkout_data, code, message
):
    with pytest.raises(ValidationError, match=message):
        place_order(cart, cart.user, checkout_data, coupon_code=code)

    assert not Order.objects.exists()
    assert cart.items.count() == 1  # the cart is untouched
