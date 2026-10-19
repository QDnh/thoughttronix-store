import re
from http import HTTPStatus

import pytest
from django.contrib.admin.sites import site
from django.db import IntegrityError
from django.urls import reverse

from orders.models import Cart

from .admin import WishlistItemInline
from .models import Wishlist, WishlistItem

# --- Model behavior ---------------------------------------------------------


def test_wishlist_str(wishlist):
    assert str(wishlist) == "Wishlist for customer"


def test_for_user_creates_the_wishlist_once(customer):
    first = Wishlist.for_user(customer)
    second = Wishlist.for_user(customer)

    assert first == second
    assert Wishlist.objects.count() == 1


def test_one_wishlist_per_user(wishlist, customer):
    with pytest.raises(IntegrityError):
        Wishlist.objects.create(user=customer)


def test_wishlist_product_pair_is_unique(wishlist, product):
    wishlist.add(product)

    with pytest.raises(IntegrityError):
        WishlistItem.objects.create(wishlist=wishlist, product=product)


def test_add_twice_has_no_extra_effect(wishlist, product):
    first = wishlist.add(product)
    second = wishlist.add(product)

    assert first == second
    assert wishlist.items.count() == 1


def test_remove_twice_has_no_extra_effect(wishlist, product):
    wishlist.add(product)

    wishlist.remove(product)
    wishlist.remove(product)

    assert not wishlist.items.exists()


def test_contains(wishlist, product, unavailable_product):
    wishlist.add(product)

    assert wishlist.contains(product)
    assert not wishlist.contains(unavailable_product)


def test_unavailable_products_can_be_saved(wishlist, unavailable_product):
    wishlist.add(unavailable_product)

    assert wishlist.contains(unavailable_product)


def test_lines_are_newest_first(wishlist, product, unavailable_product):
    wishlist.add(product)
    wishlist.add(unavailable_product)

    assert [line.product for line in wishlist.lines()] == [
        unavailable_product,
        product,
    ]


def test_deleting_the_user_deletes_the_wishlist(wishlist, product, customer):
    wishlist.add(product)

    customer.delete()

    assert not Wishlist.objects.exists()
    assert not WishlistItem.objects.exists()


def test_deleting_a_product_deletes_its_entries(wishlist, product):
    wishlist.add(product)

    product.delete()

    assert Wishlist.objects.count() == 1
    assert not WishlistItem.objects.exists()


def test_admin_registers_wishlist_with_items_inline():
    assert WishlistItemInline in site._registry[Wishlist].inlines


# --- The product-page button -------------------------------------------------


def test_anonymous_visitors_see_a_sign_in_link(client, product):
    response = client.get(product.get_absolute_url())

    page = response.content.decode()
    login = reverse("accounts:login")
    assert f'href="{login}?next={product.get_absolute_url()}"' in page
    assert "Add to wishlist" in page
    assert reverse("wishlist:add", kwargs={"pk": product.pk}) not in page


def test_product_page_shows_not_saved_state(client, customer, product):
    client.force_login(customer)

    response = client.get(product.get_absolute_url())

    page = response.content.decode()
    assert "Add to wishlist" in page
    assert reverse("wishlist:add", kwargs={"pk": product.pk}) in page


def test_product_page_shows_saved_state(client, customer, wishlist, product):
    wishlist.add(product)
    client.force_login(customer)

    response = client.get(product.get_absolute_url())

    page = response.content.decode()
    assert "In wishlist — remove" in page
    assert reverse("wishlist:remove", kwargs={"pk": product.pk}) in page


def test_saved_state_is_per_user(client, customer, wishlist, product, other_customer):
    wishlist.add(product)
    client.force_login(other_customer)

    response = client.get(product.get_absolute_url())

    assert "In wishlist — remove" not in response.content.decode()


# --- Add and remove (HTMX) ---------------------------------------------------


@pytest.mark.parametrize(
    "name", ["wishlist:add", "wishlist:remove", "wishlist:remove_from_list"]
)
def test_endpoints_require_sign_in(client, product, name):
    response = client.post(reverse(name, kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url
    assert not WishlistItem.objects.exists()


@pytest.mark.parametrize(
    "name", ["wishlist:add", "wishlist:remove", "wishlist:remove_from_list"]
)
def test_endpoints_are_post_only(client, customer, product, name):
    client.force_login(customer)

    response = client.get(reverse(name, kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_add_returns_saved_button(client, customer, product):
    client.force_login(customer)

    response = client.post(reverse("wishlist:add", kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    assert "In wishlist — remove" in page
    assert reverse("wishlist:remove", kwargs={"pk": product.pk}) in page
    assert Wishlist.for_user(customer).contains(product)


def test_add_twice_keeps_one_entry(client, customer, product):
    client.force_login(customer)
    client.post(reverse("wishlist:add", kwargs={"pk": product.pk}))

    response = client.post(reverse("wishlist:add", kwargs={"pk": product.pk}))

    assert "In wishlist — remove" in response.content.decode()
    assert WishlistItem.objects.count() == 1


def test_add_unavailable_product(client, customer, unavailable_product):
    client.force_login(customer)

    response = client.post(
        reverse("wishlist:add", kwargs={"pk": unavailable_product.pk})
    )

    assert response.status_code == HTTPStatus.OK
    assert Wishlist.for_user(customer).contains(unavailable_product)


def test_add_missing_product_404s(client, customer):
    client.force_login(customer)

    response = client.post(reverse("wishlist:add", kwargs={"pk": 9999}))

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_remove_returns_not_saved_button(client, customer, wishlist, product):
    wishlist.add(product)
    client.force_login(customer)

    response = client.post(reverse("wishlist:remove", kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    assert "Add to wishlist" in page
    assert reverse("wishlist:add", kwargs={"pk": product.pk}) in page
    assert not wishlist.contains(product)


def test_remove_unsaved_product_still_returns_not_saved(client, customer, product):
    client.force_login(customer)

    response = client.post(reverse("wishlist:remove", kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.OK
    assert "Add to wishlist" in response.content.decode()


def test_remove_works_for_unavailable_products(
    client, customer, wishlist, unavailable_product
):
    wishlist.add(unavailable_product)
    client.force_login(customer)

    client.post(reverse("wishlist:remove", kwargs={"pk": unavailable_product.pk}))

    assert not wishlist.contains(unavailable_product)


@pytest.mark.parametrize("name", ["wishlist:remove", "wishlist:remove_from_list"])
def test_cannot_remove_from_another_customers_wishlist(
    client, wishlist, product, other_customer, name
):
    """Customer A removing a product only on B's list leaves B's list alone."""
    wishlist.add(product)
    client.force_login(other_customer)

    client.post(reverse(name, kwargs={"pk": product.pk}))

    assert wishlist.contains(product)
    assert not Wishlist.for_user(other_customer).items.exists()


# --- The Wishlist page --------------------------------------------------------


def test_page_shows_only_the_signed_in_users_items(
    client, customer, wishlist, product, other_customer, unavailable_product
):
    wishlist.add(product)
    Wishlist.for_user(other_customer).add(unavailable_product)
    client.force_login(customer)

    response = client.get(reverse("wishlist:detail"))

    page = response.content.decode()
    assert product.name in page
    assert unavailable_product.name not in page


def test_empty_wishlist_shows_empty_state_without_redirecting(client, customer):
    client.force_login(customer)

    response = client.get(reverse("wishlist:detail"))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "Your wishlist is empty" in page
    # The navbar logo also links to the catalog, so match the labelled link.
    catalog = re.escape(reverse("products:catalog"))
    assert re.search(rf'<a href="{catalog}"[^>]*>\s*Browse the catalog\s*</a>', page)


def test_page_requires_sign_in(client):
    response = client.get(reverse("wishlist:detail"))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_page_lists_newest_first(
    client, customer, wishlist, product, unavailable_product
):
    wishlist.add(product)
    wishlist.add(unavailable_product)
    client.force_login(customer)

    page = client.get(reverse("wishlist:detail")).content.decode()

    assert page.index(unavailable_product.name) < page.index(product.name)


def test_rows_show_image_name_price_and_link(client, customer, wishlist, product):
    wishlist.add(product)
    client.force_login(customer)

    page = client.get(reverse("wishlist:detail")).content.decode()

    assert f'src="{product.image_url}"' in page
    assert product.name in page
    assert "$349.99" in page
    assert f'href="{product.get_absolute_url()}"' in page


@pytest.mark.parametrize("saved", [True, False])
def test_list_and_empty_state_share_one_partial(
    client, customer, wishlist, product, saved
):
    if saved:
        wishlist.add(product)
    client.force_login(customer)

    response = client.get(reverse("wishlist:detail"))

    names = [template.name for template in response.templates]
    assert "wishlist/partials/_wishlist_contents.html" in names


def test_navbar_shows_wishlist_link_when_signed_in(client, customer):
    client.force_login(customer)

    page = client.get(reverse("products:catalog")).content.decode()

    assert f'href="{reverse("wishlist:detail")}"' in page


def test_navbar_hides_wishlist_link_when_signed_out(client, db):
    page = client.get(reverse("products:catalog")).content.decode()

    assert f'href="{reverse("wishlist:detail")}"' not in page


# --- Tidy and buy from the Wishlist page --------------------------------------


def test_remove_from_list_returns_the_remaining_rows(
    client, customer, wishlist, product, unavailable_product
):
    wishlist.add(product)
    wishlist.add(unavailable_product)
    client.force_login(customer)

    response = client.post(
        reverse("wishlist:remove_from_list", kwargs={"pk": product.pk})
    )

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    assert unavailable_product.name in page
    assert product.name not in page
    assert not wishlist.contains(product)


def test_removing_the_last_item_returns_the_empty_state(
    client, customer, wishlist, product
):
    wishlist.add(product)
    client.force_login(customer)

    response = client.post(
        reverse("wishlist:remove_from_list", kwargs={"pk": product.pk})
    )

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    assert "Your wishlist is empty" in page
    assert "Browse the catalog" in page
    assert product.name not in page


def test_rows_offer_add_to_cart_and_mark_unavailable_products(
    client, customer, wishlist, product, unavailable_product
):
    wishlist.add(product)
    wishlist.add(unavailable_product)
    client.force_login(customer)

    page = client.get(reverse("wishlist:detail")).content.decode()

    assert reverse("orders:add", kwargs={"pk": product.pk}) in page
    assert reverse("orders:add", kwargs={"pk": unavailable_product.pk}) not in page
    assert re.search(r'<span class="badge[^"]*">\s*Unavailable\s*</span>', page)
    assert re.search(r"<button[^>]*disabled[^>]*>\s*Unavailable\s*</button>", page)


def test_rows_have_a_remove_button_targeting_the_contents(
    client, customer, wishlist, product
):
    wishlist.add(product)
    client.force_login(customer)

    page = client.get(reverse("wishlist:detail")).content.decode()

    assert reverse("wishlist:remove_from_list", kwargs={"pk": product.pk}) in page
    assert 'hx-target="#wishlist-contents"' in page


def test_adding_to_the_cart_keeps_the_wishlist_item(
    client, customer, wishlist, product
):
    wishlist.add(product)
    client.force_login(customer)

    client.post(reverse("orders:add", kwargs={"pk": product.pk}))

    assert Cart.for_user(customer).items.filter(product=product).exists()
    assert wishlist.contains(product)


def test_products_that_become_unavailable_stay_on_the_list(
    client, customer, wishlist, product
):
    wishlist.add(product)
    product.is_available = False
    product.save()
    client.force_login(customer)

    page = client.get(reverse("wishlist:detail")).content.decode()

    assert product.name in page
    assert reverse("orders:add", kwargs={"pk": product.pk}) not in page
