"""Discount codes: the validity rules, the checkout Apply flow, the back office."""

from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from products.models import Product

from .forms import DiscountCodeForm
from .models import DiscountCode, Order
from .services import place_order
from .test_checkout_form import VALID_DATA

pytestmark = pytest.mark.django_db


def check(text, products, **kwargs):
    return DiscountCode.objects.for_checkout(text, products, **kwargs)


# --- Validity: the four messages ---------------------------------------------


def test_a_running_code_is_found_case_and_space_insensitively(order_code, product):
    assert check("  thoughts15 ", [product]) == order_code


def test_an_unknown_code_is_rejected(product):
    with pytest.raises(ValidationError, match="We don't recognize that code."):
        check("NOPE", [product])


def test_an_expired_code_names_its_end_date(expired_code, product):
    with pytest.raises(ValidationError) as caught:
        check("SPRING20", [product])

    assert caught.value.messages == [
        f"This code expired on {expired_code.expires_display}."
    ]


def test_a_scheduled_code_names_its_start_date(scheduled_code, product):
    with pytest.raises(ValidationError) as caught:
        check("HOLIDAY25", [product])

    assert caught.value.messages == [
        f"This code isn't active until {scheduled_code.starts_display}."
    ]


def test_the_window_includes_its_start_and_excludes_its_end(order_code, product):
    assert check("THOUGHTS15", [product], now=order_code.starts_at) == order_code
    with pytest.raises(ValidationError, match="expired"):
        check("THOUGHTS15", [product], now=order_code.expires_at)


def test_a_product_code_with_nothing_eligible_is_rejected(seraphine_code, category):
    pillow = Product.objects.create(
        name="Charging Pillow", slug="pillow", price=Decimal("69.00"), category=category
    )

    with pytest.raises(
        ValidationError, match="SERAPHINE50 doesn't apply to anything in your cart."
    ):
        check("SERAPHINE50", [pillow])


# --- Model behavior ----------------------------------------------------------


def test_discount_for_rounds_half_up_per_line(order_code, product):
    # 15% of 33.33 = 4.9995 → 5.00
    assert order_code.discount_for(product, Decimal("33.33")) == Decimal("5.00")


def test_a_product_code_covers_only_its_products(seraphine_code, product, category):
    other = Product.objects.create(
        name="Other", slug="other", price=Decimal("1.00"), category=category
    )

    assert seraphine_code.covers(product)
    assert not seraphine_code.covers(other)
    assert seraphine_code.discount_for(other, Decimal("10.00")) == Decimal("0.00")


def test_status(order_code, expired_code, scheduled_code):
    assert order_code.status() == DiscountCode.Status.ACTIVE
    assert expired_code.status() == DiscountCode.Status.EXPIRED
    assert scheduled_code.status() == DiscountCode.Status.SCHEDULED


@pytest.mark.parametrize("fixture", ["order_code", "scheduled_code"])
def test_end_now_expires_running_and_scheduled_codes(request, fixture):
    code = request.getfixturevalue(fixture)

    code.end_now()

    code.refresh_from_db()
    assert code.status() == DiscountCode.Status.EXPIRED


# --- Checkout: the Apply button (HTMX) ----------------------------------------


def apply(client, text):
    return client.post(reverse("orders:apply_discount"), {"discount_code": text})


def test_apply_requires_login(client, cart_item):
    response = apply(client, "THOUGHTS15")

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_apply_previews_the_discount_as_a_partial(
    client, customer, cart_item, order_code
):
    client.force_login(customer)

    response = apply(client, "thoughts15")

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    assert "THOUGHTS15 applied" in page
    assert "−$105.00" in page
    assert "$594.98" in page
    assert 'id="place-order-total" hx-swap-oob="true"' in page
    assert not Order.objects.exists()  # a preview saves nothing


def test_apply_with_an_expired_code_shows_the_message_not_a_broken_page(
    client, customer, cart_item, expired_code
):
    client.force_login(customer)

    response = apply(client, "SPRING20")

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "This code expired on" in page
    assert "$699.98" in page  # full price — a rejected code discounts nothing


def test_apply_with_a_blank_code_clears_the_discount(client, customer, cart_item):
    client.force_login(customer)

    page = apply(client, "").content.decode()

    assert "applied" not in page
    assert "$699.98" in page


# --- Checkout: placing the order ---------------------------------------------


def checkout(client, **extra):
    return client.post(reverse("orders:checkout"), {**VALID_DATA, **extra})


def test_checkout_with_a_code_places_a_discounted_order(
    client, customer, cart_item, seraphine_code
):
    client.force_login(customer)

    response = checkout(client, discount_code="seraphine50")

    order = Order.objects.get()
    assert response.status_code == HTTPStatus.FOUND
    assert order.total == Decimal("349.99")
    assert order.discount_code_text == "SERAPHINE50"


def test_checkout_with_an_expired_code_rerenders_with_the_message(
    client, customer, cart_item, expired_code
):
    client.force_login(customer)

    response = checkout(client, discount_code="SPRING20")

    assert response.status_code == HTTPStatus.OK
    assert "This code expired on" in response.content.decode()
    assert not Order.objects.exists()
    assert customer.cart.items.exists()


def test_a_code_that_expires_during_checkout_is_caught(
    client, customer, cart_item, order_code, monkeypatch
):
    """The form accepted it, then place_order's re-check refuses it."""
    client.force_login(customer)
    original = DiscountCode.objects.for_checkout
    calls = {"count": 0}

    def expire_on_second_check(text, products, **kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            kwargs["now"] = order_code.expires_at
        return original(text, products, **kwargs)

    monkeypatch.setattr(DiscountCode.objects, "for_checkout", expire_on_second_check)

    response = checkout(client, discount_code="THOUGHTS15")

    assert response.status_code == HTTPStatus.OK
    assert "This code expired on" in response.content.decode()
    assert not Order.objects.exists()


def test_order_pages_show_the_snapshotted_discount(
    client, customer, cart_item, order_code
):
    order = place_order(
        customer.cart, customer, dict(VALID_DATA), coupon_code="THOUGHTS15"
    )
    client.force_login(customer)

    detail = client.get(reverse("orders:detail", kwargs={"pk": order.pk}))
    confirmation = client.get(reverse("orders:confirmation", kwargs={"pk": order.pk}))

    assert "THOUGHTS15 (15% off)" in detail.content.decode()
    assert "−$105.00" in detail.content.decode()
    assert "THOUGHTS15 saved you $105.00" in confirmation.content.decode()


# --- The back office -----------------------------------------------------------


def valid_form_data(**overrides):
    now = timezone.localtime()
    return {
        "code": "WINTER10",
        "percent_off": 10,
        "applies_to": DiscountCode.AppliesTo.ORDER,
        "starts_at": now.strftime("%Y-%m-%dT%H:%M"),
        "expires_at": (now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M"),
        **overrides,
    }


def manage_urls(code):
    return [
        reverse("orders:manage_discounts"),
        reverse("orders:manage_discount_create"),
        reverse("orders:manage_discount_update", kwargs={"pk": code.pk}),
        reverse("orders:manage_discount_end", kwargs={"pk": code.pk}),
        reverse("orders:manage_discount_delete", kwargs={"pk": code.pk}),
    ]


def test_anonymous_users_are_sent_to_login(client, order_code):
    for url in manage_urls(order_code):
        response = client.get(url)

        assert response.status_code == HTTPStatus.FOUND, url
        assert reverse("accounts:login") in response.url


def test_customers_get_403(client, customer, order_code):
    client.force_login(customer)

    for url in manage_urls(order_code):
        assert client.get(url).status_code == HTTPStatus.FORBIDDEN, url


def test_list_shows_each_code_with_status(
    client, staff_user, order_code, expired_code, scheduled_code
):
    client.force_login(staff_user)

    page = client.get(reverse("orders:manage_discounts")).content.decode()

    for code in ("THOUGHTS15", "SPRING20", "HOLIDAY25"):
        assert code in page
    assert "Active" in page
    assert "Expired" in page
    assert "Scheduled" in page


def test_list_filters_by_status(client, staff_user, order_code, expired_code):
    client.force_login(staff_user)

    page = client.get(
        reverse("orders:manage_discounts"), {"status": "expired"}
    ).content.decode()

    assert "SPRING20" in page
    assert "THOUGHTS15" not in page


def test_list_has_designed_empty_states(client, staff_user, order_code):
    client.force_login(staff_user)

    assert "No codes with that status" in (
        client.get(
            reverse("orders:manage_discounts"), {"status": "expired"}
        ).content.decode()
    )
    order_code.delete()
    assert "No discount codes yet" in (
        client.get(reverse("orders:manage_discounts")).content.decode()
    )


def test_staff_can_create_a_code(client, staff_user, product):
    client.force_login(staff_user)

    client.post(
        reverse("orders:manage_discount_create"),
        valid_form_data(
            code="seraphine50",
            percent_off=50,
            applies_to=DiscountCode.AppliesTo.PRODUCTS,
            products=[product.pk],
        ),
    )

    code = DiscountCode.objects.get()
    assert code.code == "SERAPHINE50"  # stored uppercase
    assert list(code.products.all()) == [product]


def test_form_accepts_valid_data(db):
    assert DiscountCodeForm(data=valid_form_data()).is_valid()


def test_specific_products_requires_a_product(db):
    form = DiscountCodeForm(
        data=valid_form_data(applies_to=DiscountCode.AppliesTo.PRODUCTS)
    )

    assert not form.is_valid()
    assert form.errors["products"] == ["Pick at least one product."]


def test_entire_order_refuses_products(product):
    form = DiscountCodeForm(data=valid_form_data(products=[product.pk]))

    assert not form.is_valid()
    assert "products" in form.errors


def test_the_code_must_end_after_it_starts(db):
    data = valid_form_data()
    form = DiscountCodeForm(data={**data, "expires_at": data["starts_at"]})

    assert not form.is_valid()
    assert form.errors["expires_at"] == ["The code must end after it starts."]


def test_expires_at_is_required(db):
    form = DiscountCodeForm(data=valid_form_data(expires_at=""))

    assert not form.is_valid()
    assert "expires_at" in form.errors


@pytest.mark.parametrize("percent", [0, 101])
def test_percent_must_be_1_to_100(db, percent):
    form = DiscountCodeForm(data=valid_form_data(percent_off=percent))

    assert not form.is_valid()
    assert "percent_off" in form.errors


def test_codes_are_unique_regardless_of_case(order_code):
    form = DiscountCodeForm(data=valid_form_data(code="thoughts15"))

    assert not form.is_valid()
    assert "code" in form.errors


def test_end_now_retires_a_code(client, staff_user, order_code):
    client.force_login(staff_user)

    response = client.post(
        reverse("orders:manage_discount_end", kwargs={"pk": order_code.pk}),
        follow=True,
    )

    order_code.refresh_from_db()
    assert order_code.status() == DiscountCode.Status.EXPIRED
    assert "THOUGHTS15 has ended." in response.content.decode()


def test_an_unused_code_can_be_deleted(client, staff_user, order_code):
    client.force_login(staff_user)

    client.post(reverse("orders:manage_discount_delete", kwargs={"pk": order_code.pk}))

    assert not DiscountCode.objects.exists()


def test_a_used_code_cannot_be_deleted(client, staff_user, cart_item, order_code):
    place_order(
        cart_item.cart, cart_item.cart.user, dict(VALID_DATA), coupon_code="THOUGHTS15"
    )
    client.force_login(staff_user)
    url = reverse("orders:manage_discount_delete", kwargs={"pk": order_code.pk})

    assert client.get(url).status_code == HTTPStatus.NOT_FOUND
    assert client.post(url).status_code == HTTPStatus.NOT_FOUND
    assert DiscountCode.objects.exists()
