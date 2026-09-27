"""Saved addresses at checkout: pre-fill, the HTMX refill, and save-on-order."""

from http import HTTPStatus

from django.urls import reverse

from .models import Order
from .test_checkout_form import VALID_DATA

# --- Pre-fill and the dropdown ------------------------------------------------


def test_checkout_prefills_from_the_default_addresses(
    client, customer, cart_item, address, second_address
):
    second_address.make_default_billing()
    client.force_login(customer)

    form = client.get(reverse("orders:checkout")).context["form"]

    assert form.initial["shipping_street"] == "214 Synapse Street"
    assert form.initial["billing_street"] == "2600 Neuron Parkway"
    assert form.initial["billing_line2"] == "Suite 400"


def test_checkout_without_saved_addresses_is_blank_and_has_no_dropdown(
    client, customer, cart_item
):
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"))

    assert "shipping_street" not in response.context["form"].initial
    assert "Use a saved address" not in response.content.decode()


def test_checkout_without_defaults_still_offers_the_dropdown(
    client, customer, cart_item, address
):
    customer.addresses.update(is_default_shipping=False, is_default_billing=False)
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"))

    assert "shipping_street" not in response.context["form"].initial
    assert "Use a saved address" in response.content.decode()


def test_the_dropdown_lists_only_the_customers_addresses(
    client, customer, cart_item, second_address, other_address
):
    client.force_login(customer)

    page = client.get(reverse("orders:checkout")).content.decode()

    assert "2600 Neuron Parkway" in page
    assert "9 Axon Avenue" not in page


# --- The HTMX refill endpoint -------------------------------------------------


def test_address_fields_returns_the_partial_filled_in(client, customer, second_address):
    client.force_login(customer)

    response = client.get(
        reverse("orders:address_fields", kwargs={"section": "billing"}),
        {"address": second_address.pk},
    )

    assert response.status_code == HTTPStatus.OK
    assert [t.name for t in response.templates][0] == (
        "orders/partials/_address_fields.html"
    )
    page = response.content.decode()
    assert 'name="billing_street"' in page
    assert 'value="2600 Neuron Parkway"' in page
    assert "shipping_" not in page
    assert "<html" not in page  # a partial, never base.html


def test_address_fields_blank_choice_returns_empty_fields(client, customer, address):
    client.force_login(customer)

    response = client.get(
        reverse("orders:address_fields", kwargs={"section": "shipping"}),
        {"address": ""},
    )

    page = response.content.decode()
    assert 'name="shipping_street"' in page
    assert "214 Synapse Street" not in page


def test_address_fields_rejects_anothers_address(client, customer, other_address):
    client.force_login(customer)

    response = client.get(
        reverse("orders:address_fields", kwargs={"section": "shipping"}),
        {"address": other_address.pk},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_address_fields_rejects_bad_input(client, customer, address):
    client.force_login(customer)
    url = reverse("orders:address_fields", kwargs={"section": "shipping"})

    assert client.get(url, {"address": "abc"}).status_code == HTTPStatus.NOT_FOUND
    assert (
        client.get(
            reverse("orders:address_fields", kwargs={"section": "card"}),
            {"address": address.pk},
        ).status_code
        == HTTPStatus.NOT_FOUND
    )


def test_address_fields_requires_login(client, db):
    response = client.get(
        reverse("orders:address_fields", kwargs={"section": "shipping"})
    )

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


# --- Saving from checkout ----------------------------------------------------


def test_ticked_boxes_save_the_addresses(client, customer, cart_item):
    client.force_login(customer)

    client.post(
        reverse("orders:checkout"),
        {**VALID_DATA, "save_shipping": "on", "save_billing": "on"},
    )

    assert Order.objects.exists()
    # Shipping and billing differ in line2 and ZIP, so both are kept.
    assert customer.addresses.count() == 2
    first = customer.addresses.first()
    assert first.line2 == "Unit 7"
    assert first.is_default_shipping
    assert first.is_default_billing


def test_unticked_boxes_save_nothing(client, customer, cart_item):
    client.force_login(customer)

    client.post(reverse("orders:checkout"), VALID_DATA)

    assert Order.objects.exists()
    assert not customer.addresses.exists()


def test_resaving_a_saved_address_creates_no_duplicate(client, customer, cart, product):
    client.force_login(customer)
    for _ in range(2):
        cart.add(product)
        client.post(reverse("orders:checkout"), {**VALID_DATA, "save_shipping": "on"})

    assert Order.objects.count() == 2
    assert customer.addresses.count() == 1


def test_a_failed_checkout_saves_no_address(client, customer, cart_item):
    client.force_login(customer)

    client.post(
        reverse("orders:checkout"),
        {**VALID_DATA, "card_number": "4242 4242 4242 4241", "save_shipping": "on"},
    )

    assert not Order.objects.exists()
    assert not customer.addresses.exists()


def test_editing_a_saved_address_leaves_the_order_alone(client, customer, cart_item):
    client.force_login(customer)
    client.post(reverse("orders:checkout"), {**VALID_DATA, "save_shipping": "on"})

    customer.addresses.update(street="1 Moved Away Road")

    assert Order.objects.get().shipping_street == "12 Cortex Lane"
