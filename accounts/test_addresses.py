"""The address book: model rules, the checkout-save manager, and its pages."""

from http import HTTPStatus

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from orders.test_checkout_form import VALID_DATA

from .models import Address

NEW_ADDRESS = {
    "name": "Casey Monroe",
    "street": "77 Cortex Lane",
    "line2": "",
    "city": "Amarillo",
    "state": "TX",
    "zip": "79101",
}

# --- Model rules -------------------------------------------------------------


def test_str_summarizes_the_address(second_address):
    assert str(second_address) == (
        "Casey Monroe — 2600 Neuron Parkway, Suite 400, Amarillo, TX 79101"
    )


def test_the_first_address_becomes_both_defaults(address):
    assert address.is_default_shipping
    assert address.is_default_billing


def test_a_later_address_never_replaces_an_existing_default(address, second_address):
    assert not second_address.is_default_shipping
    assert not second_address.is_default_billing


def test_a_new_address_fills_only_the_empty_slot(address, second_address):
    second_address.make_default_billing()
    address.refresh_from_db()
    address.delete()  # home held shipping only; that slot is now empty

    third = Address.objects.create(user=address.user, **NEW_ADDRESS)

    assert third.is_default_shipping
    assert not third.is_default_billing


def test_make_default_moves_the_flag(address, second_address):
    second_address.make_default_shipping()

    address.refresh_from_db()
    second_address.refresh_from_db()
    assert second_address.is_default_shipping
    assert not address.is_default_shipping
    assert address.is_default_billing  # the other kind is untouched


def test_the_database_allows_one_default_of_each_kind(address, second_address):
    with pytest.raises(IntegrityError), transaction.atomic():
        Address.objects.filter(pk=second_address.pk).update(is_default_shipping=True)


def test_defaults_are_per_user(address, other_address):
    assert other_address.is_default_shipping
    assert other_address.is_default_billing


def test_deleting_a_default_leaves_the_slot_empty(address, second_address):
    address.delete()

    second_address.refresh_from_db()
    assert not second_address.is_default_shipping
    assert not second_address.is_default_billing


# --- Saving from checkout ----------------------------------------------------


def test_save_from_checkout_maps_the_prefixed_fields(customer):
    saved = Address.objects.save_from_checkout(customer, VALID_DATA, prefix="shipping_")

    assert saved.user == customer
    assert saved.street == "12 Cortex Lane"
    assert saved.line2 == "Unit 7"
    assert saved.zip == "79015"


def test_save_from_checkout_skips_exact_duplicates(customer):
    first = Address.objects.save_from_checkout(customer, VALID_DATA, prefix="shipping_")
    again = Address.objects.save_from_checkout(customer, VALID_DATA, prefix="shipping_")

    assert again == first
    assert customer.addresses.count() == 1


def test_save_from_checkout_keeps_near_duplicates(customer):
    Address.objects.save_from_checkout(customer, VALID_DATA, prefix="shipping_")
    Address.objects.save_from_checkout(customer, VALID_DATA, prefix="billing_")

    # Same street, different line2 and ZIP — two distinct addresses.
    assert customer.addresses.count() == 2


# --- The address book pages --------------------------------------------------


def test_address_book_requires_login(client, db):
    response = client.get(reverse("accounts:addresses"))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_address_book_has_a_designed_empty_state(client, customer):
    client.force_login(customer)

    response = client.get(reverse("accounts:addresses"))

    assert "No saved addresses yet" in response.content.decode()


def test_address_book_lists_only_the_customers_addresses(
    client, customer, second_address, other_address
):
    client.force_login(customer)

    page = client.get(reverse("accounts:addresses")).content.decode()

    assert "214 Synapse Street" in page
    assert "2600 Neuron Parkway" in page
    assert "Default shipping" in page
    assert "9 Axon Avenue" not in page


def test_address_book_hints_at_an_empty_default_slot(client, customer, second_address):
    second_address.make_default_shipping()
    second_address.user.addresses.exclude(pk=second_address.pk).delete()
    client.force_login(customer)

    page = " ".join(client.get(reverse("accounts:addresses")).content.decode().split())

    assert "No default billing address" in page


def test_adding_an_address(client, customer):
    client.force_login(customer)

    response = client.post(reverse("accounts:address_create"), NEW_ADDRESS)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("accounts:addresses")
    saved = customer.addresses.get()
    assert saved.street == "77 Cortex Lane"
    assert saved.is_default_shipping  # the first address fills both slots


def test_adding_an_invalid_address_shows_field_errors(client, customer):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:address_create"), {**NEW_ADDRESS, "zip": "790"}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["zip"]
    assert not customer.addresses.exists()


def test_editing_an_address(client, customer, address):
    client.force_login(customer)

    client.post(
        reverse("accounts:address_update", kwargs={"pk": address.pk}),
        {**NEW_ADDRESS, "street": "1 Renamed Road"},
    )

    address.refresh_from_db()
    assert address.street == "1 Renamed Road"
    assert address.is_default_shipping  # editing keeps the defaults


def test_deleting_an_address(client, customer, address):
    client.force_login(customer)

    confirm = client.get(reverse("accounts:address_delete", kwargs={"pk": address.pk}))
    response = client.post(
        reverse("accounts:address_delete", kwargs={"pk": address.pk})
    )

    assert confirm.status_code == HTTPStatus.OK
    assert response.url == reverse("accounts:addresses")
    assert not customer.addresses.exists()


def test_make_default_buttons(client, customer, address, second_address):
    client.force_login(customer)

    client.post(
        reverse("accounts:address_default_shipping", kwargs={"pk": second_address.pk})
    )
    client.post(
        reverse("accounts:address_default_billing", kwargs={"pk": second_address.pk})
    )

    second_address.refresh_from_db()
    assert second_address.is_default_shipping
    assert second_address.is_default_billing


def test_make_default_is_post_only(client, customer, second_address):
    client.force_login(customer)

    response = client.get(
        reverse("accounts:address_default_shipping", kwargs={"pk": second_address.pk})
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


@pytest.mark.parametrize(
    ("name", "method"),
    [
        ("accounts:address_update", "get"),
        ("accounts:address_update", "post"),
        ("accounts:address_delete", "get"),
        ("accounts:address_delete", "post"),
        ("accounts:address_default_shipping", "post"),
        ("accounts:address_default_billing", "post"),
    ],
)
def test_customers_cannot_touch_anothers_address(
    client, customer, other_address, name, method
):
    client.force_login(customer)
    url = reverse(name, kwargs={"pk": other_address.pk})

    response = getattr(client, method)(url, NEW_ADDRESS if method == "post" else None)

    assert response.status_code == HTTPStatus.NOT_FOUND
    other_address.refresh_from_db()
    assert other_address.street == "9 Axon Avenue"


def test_navbar_links_to_the_address_book(client, customer):
    client.force_login(customer)

    page = client.get(reverse("products:catalog")).content.decode()

    assert reverse("accounts:addresses") in page
