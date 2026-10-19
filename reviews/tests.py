import re
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

import pytest
from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from orders.models import Order

from .models import COMMENT_MAX_LENGTH, Review, ReviewManager

NOT_RECEIVED = "Only customers who've received this product can review it."

# --- Model behavior ---------------------------------------------------------


def test_summary_is_the_average_and_count_in_one_query(
    review, product, other_customer, staff_user, django_assert_num_queries
):
    Review.objects.create(author=other_customer, product=product, rating=5, comment="!")
    Review.objects.create(author=staff_user, product=product, rating=4, comment="Ok.")

    with django_assert_num_queries(1):
        summary = product.reviews.summary()

    assert summary == {"average": pytest.approx(13 / 3), "count": 3}


def test_summary_of_no_reviews(product):
    assert product.reviews.summary() == {"average": None, "count": 0}


@pytest.mark.parametrize(
    ("edited", "by_staff", "expected"),
    [
        (False, False, ""),
        (True, False, "Edited"),
        (True, True, "Edited by staff"),
    ],
)
def test_edit_label(review, edited, by_staff, expected):
    if edited:
        review.updated_at = review.created_at + timedelta(hours=1)
    review.edited_by_staff = by_staff
    review.save()
    review.refresh_from_db()

    assert review.edit_label == expected


def test_one_review_per_author_per_product(review, customer, product):
    with pytest.raises(IntegrityError):
        Review.objects.create(author=customer, product=product, rating=1, comment="x")


def test_the_same_author_can_review_another_product(review, customer, featured_product):
    Review.objects.create(
        author=customer, product=featured_product, rating=3, comment="Fine."
    )

    assert customer.reviews.count() == 2


@pytest.mark.parametrize("rating", [None, 0, 6])
def test_rating_must_be_one_to_five(review, rating):
    review.rating = rating

    with pytest.raises(ValidationError) as error:
        review.full_clean()

    assert "rating" in error.value.message_dict


@pytest.mark.parametrize("rating", [1, 5])
def test_ratings_at_the_bounds_are_valid(review, rating):
    review.rating = rating

    review.full_clean()


@pytest.mark.parametrize("comment", ["", "x" * (COMMENT_MAX_LENGTH + 1)])
def test_comment_is_required_and_capped(review, comment):
    review.comment = comment

    with pytest.raises(ValidationError) as error:
        review.full_clean()

    assert "comment" in error.value.message_dict


def test_comment_at_the_limit_is_valid(review):
    review.comment = "x" * COMMENT_MAX_LENGTH

    review.full_clean()


def test_deleting_the_author_deletes_their_reviews(review, customer):
    customer.delete()

    assert not Review.objects.exists()


def test_deleting_the_product_deletes_its_reviews(review, product):
    product.delete()

    assert not Review.objects.exists()


def test_reviews_are_newest_first(review, product, other_customer):
    review.created_at = timezone.now() - timedelta(days=2)
    review.save()
    newer = Review.objects.create(
        author=other_customer, product=product, rating=2, comment="Meh."
    )

    assert list(product.reviews.all()) == [newer, review]


def test_can_review_needs_a_delivered_purchase_and_no_review_yet(
    order_with, customer, product
):
    assert not Review.objects.can_review(customer, product)

    order_with(customer, product)
    assert Review.objects.can_review(customer, product)

    Review.objects.create(author=customer, product=product, rating=5, comment="Yes.")
    assert not Review.objects.can_review(customer, product)


def test_admin_registers_review():
    assert Review in site._registry


# --- The product-page section ------------------------------------------------


def test_product_page_renders_the_reviews_section(client, review, product):
    response = client.get(product.get_absolute_url())

    names = [template.name for template in response.templates]
    assert "reviews/partials/_reviews_section.html" in names


def test_section_shows_summary_and_verified_note(
    client, review, product, other_customer
):
    Review.objects.create(author=other_customer, product=product, rating=5, comment="!")

    page = client.get(product.get_absolute_url()).content.decode()

    assert "4.5</span> out of 5" in page
    assert "2 reviews" in page
    assert "verified buyer" in page
    assert "No reviews yet" not in page


def test_a_single_review_is_not_pluralized(client, review, product):
    page = client.get(product.get_absolute_url()).content.decode()

    assert "1 review" in page
    assert "1 reviews" not in page


def test_product_without_reviews_shows_the_empty_state(client, product):
    page = client.get(product.get_absolute_url()).content.decode()

    assert "No reviews yet" in page
    assert "verified buyer" not in page


def test_card_shows_name_rating_date_and_comment(client, product):
    author = get_user_model().objects.create_user(
        username="casey_login_7",
        email="casey@example.com",
        password="x",
        first_name="Casey",
        last_name="Monroe",
    )
    Review.objects.create(
        author=author,
        product=product,
        rating=3,
        comment="Mostly listens.",
        created_at=datetime(2026, 10, 18, 12, tzinfo=UTC),
    )

    page = client.get(product.get_absolute_url()).content.decode()

    assert "Casey M." in page
    assert 'aria-label="3 out of 5 stars"' in page
    assert "Oct 18, 2026" in page
    assert "Mostly listens." in page
    assert "casey_login_7" not in page


def test_page_lists_reviews_newest_first(client, review, product, other_customer):
    review.created_at = timezone.now() - timedelta(days=2)
    review.save()
    Review.objects.create(
        author=other_customer, product=product, rating=2, comment="Newer opinion."
    )

    page = client.get(product.get_absolute_url()).content.decode()

    assert page.index("Newer opinion.") < page.index(review.comment)


@pytest.mark.parametrize(
    ("by_staff", "label"), [(False, "Edited"), (True, "Edited by staff")]
)
def test_cards_show_the_edit_label(client, review, product, by_staff, label):
    review.updated_at = review.created_at + timedelta(hours=1)
    review.edited_by_staff = by_staff
    review.save()

    page = client.get(product.get_absolute_url()).content.decode()

    assert f">{label}</span>" in page


def test_unedited_cards_have_no_label(client, review, product):
    page = client.get(product.get_absolute_url()).content.decode()

    assert ">Edited" not in page


def test_unavailable_products_show_their_reviews(client, customer, unavailable_product):
    Review.objects.create(
        author=customer, product=unavailable_product, rating=5, comment="Miss it."
    )

    page = client.get(unavailable_product.get_absolute_url()).content.decode()

    assert "Miss it." in page
    assert "1 review" in page


# --- Writing a review (HTMX) --------------------------------------------------


def test_a_double_submit_leaves_one_review_and_resends_the_section(
    client, order_with, customer, product
):
    order_with(customer, product)
    client.force_login(customer)
    url = reverse("reviews:create", args=[product.pk])
    data = {"rating": 5, "comment": "Worth every thought."}

    client.post(url, data)
    client.raise_request_exception = False  # see a server error as a browser would
    second = client.post(url, data)

    assert second.status_code == HTTPStatus.OK
    assert Review.objects.filter(author=customer, product=product).count() == 1
    assert "Worth every thought." in second.content.decode()


def test_a_simultaneous_submit_is_not_a_server_error(
    client, monkeypatch, order_with, review, customer, product
):
    # Both requests passed the eligibility check before either saved.
    monkeypatch.setattr(ReviewManager, "can_review", lambda self, user, product: True)
    client.force_login(customer)

    response = client.post(
        reverse("reviews:create", args=[product.pk]),
        {"rating": 1, "comment": "The race loser."},
    )

    assert response.status_code == HTTPStatus.OK
    assert list(Review.objects.all()) == [review]


def test_create_posts_the_review_and_resends_the_section(
    client, order_with, customer, product, other_customer
):
    order_with(customer, product)
    Review.objects.create(
        author=other_customer, product=product, rating=2, comment="Too chatty."
    )
    client.force_login(customer)

    response = client.post(
        reverse("reviews:create", args=[product.pk]),
        {"rating": 5, "comment": "Worth every thought."},
    )

    page = response.content.decode()
    names = [template.name for template in response.templates]
    assert response.status_code == HTTPStatus.OK
    assert "base.html" not in names
    assert 'id="reviews"' in page
    review = Review.objects.get(author=customer, product=product)
    assert (review.rating, review.comment) == (5, "Worth every thought.")
    assert "3.5</span> out of 5" in page
    assert "2 reviews" in page
    assert page.index("Worth every thought.") < page.index("Too chatty.")
    assert "Post review" not in page


def test_create_requires_sign_in(client, product):
    response = client.post(
        reverse("reviews:create", args=[product.pk]),
        {"rating": 5, "comment": "Anonymous praise."},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url
    assert not Review.objects.exists()


def test_create_is_post_only(client, order_with, customer, product):
    order_with(customer, product)
    client.force_login(customer)

    response = client.get(reverse("reviews:create", args=[product.pk]))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_create_for_a_missing_product_is_404(client, customer):
    client.force_login(customer)

    response = client.post(
        reverse("reviews:create", args=[999]), {"rating": 5, "comment": "?"}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_create_works_on_an_unavailable_product(
    client, order_with, customer, unavailable_product
):
    order_with(customer, unavailable_product)
    client.force_login(customer)

    response = client.post(
        reverse("reviews:create", args=[unavailable_product.pk]),
        {"rating": 4, "comment": "Miss it already."},
    )

    assert response.status_code == HTTPStatus.OK
    assert Review.objects.filter(product=unavailable_product).count() == 1


def test_create_is_rejected_without_a_delivered_purchase(
    client, order_with, customer, product
):
    order_with(customer, product, status=Order.Status.SHIPPED)
    client.force_login(customer)

    response = client.post(
        reverse("reviews:create", args=[product.pk]),
        {"rating": 5, "comment": "Can't wait for it."},
    )

    assert response.status_code == HTTPStatus.OK
    assert not Review.objects.exists()
    assert NOT_RECEIVED in response.content.decode()


def test_create_is_rejected_after_the_order_leaves_delivered(
    client, order_with, customer, product
):
    order = order_with(customer, product)
    client.force_login(customer)
    client.get(product.get_absolute_url())  # The form was on screen.
    order.status = Order.Status.CANCELLED
    order.save()

    response = client.post(
        reverse("reviews:create", args=[product.pk]),
        {"rating": 5, "comment": "Stale form."},
    )

    assert response.status_code == HTTPStatus.OK
    assert not Review.objects.exists()
    assert NOT_RECEIVED in response.content.decode()


@pytest.mark.parametrize(
    ("data", "field", "error"),
    [
        ({"comment": "Forgot the stars."}, "rating", "Choose a star rating."),
        ({"rating": 3, "comment": "   "}, "comment", "Write a comment"),
        (
            {"rating": 3, "comment": "x" * (COMMENT_MAX_LENGTH + 1)},
            "comment",
            "at most 2000 characters",
        ),
    ],
)
def test_invalid_create_shows_errors_and_keeps_the_input(
    client, order_with, customer, product, data, field, error
):
    order_with(customer, product)
    client.force_login(customer)

    response = client.post(reverse("reviews:create", args=[product.pk]), data)

    page = response.content.decode()
    assert response.status_code == HTTPStatus.OK
    assert not Review.objects.exists()
    assert error in page
    assert "Post review" in page
    if data.get("rating"):
        assert re.search(rf'value="{data["rating"]}"[^>]*checked', page)
    if data["comment"].strip():
        assert data["comment"] in page


# --- Viewer states on the product page ----------------------------------------


def radio_inputs(page):
    return re.findall(r'<input type="radio"[^>]*>', page)


def test_visitors_get_a_sign_in_link_back_to_the_product(client, product):
    page = client.get(product.get_absolute_url()).content.decode()

    login = reverse("accounts:login")
    assert f'href="{login}?next={product.get_absolute_url()}"' in page
    assert "Post review" not in page
    assert NOT_RECEIVED not in page


def test_customers_who_never_ordered_see_the_not_received_message(
    client, customer, product
):
    client.force_login(customer)

    page = client.get(product.get_absolute_url()).content.decode()

    assert NOT_RECEIVED in page
    assert "Post review" not in page


@pytest.mark.parametrize("status", [Order.Status.PLACED, Order.Status.SHIPPED])
def test_customers_awaiting_delivery_see_the_not_received_message(
    client, order_with, customer, product, status
):
    order_with(customer, product, status=status)
    client.force_login(customer)

    page = client.get(product.get_absolute_url()).content.decode()

    assert NOT_RECEIVED in page
    assert "Post review" not in page


def test_eligible_customers_get_the_form_with_no_star_chosen(
    client, order_with, customer, product
):
    order_with(customer, product)
    client.force_login(customer)

    page = client.get(product.get_absolute_url()).content.decode()

    assert "Post review" in page
    assert reverse("reviews:create", args=[product.pk]) in page
    stars = radio_inputs(page)
    assert len(stars) == 5
    assert not any("checked" in star for star in stars)
    assert NOT_RECEIVED not in page


def test_reviewers_see_their_review_pinned_and_no_form(
    client, order_with, review, customer, product, other_customer
):
    order_with(customer, product)
    review.created_at = timezone.now() - timedelta(days=5)
    review.save()
    Review.objects.create(
        author=other_customer, product=product, rating=1, comment="Newer, sadder."
    )
    client.force_login(customer)

    page = client.get(product.get_absolute_url()).content.decode()

    assert "Post review" not in page
    assert NOT_RECEIVED not in page
    assert page.index(review.comment) < page.index("Newer, sadder.")


def test_other_viewers_see_newest_first_without_pinning(
    client, review, product, other_customer
):
    review.created_at = timezone.now() - timedelta(days=5)
    review.save()
    Review.objects.create(
        author=other_customer, product=product, rating=1, comment="Newer, sadder."
    )
    client.force_login(other_customer)

    page = client.get(product.get_absolute_url()).content.decode()

    assert page.index("Newer, sadder.") < page.index(review.comment)


def test_staff_without_a_delivery_see_the_not_received_message(
    client, staff_user, product
):
    client.force_login(staff_user)

    page = client.get(product.get_absolute_url()).content.decode()

    assert NOT_RECEIVED in page
    assert "Post review" not in page


def test_staff_with_a_delivery_get_the_form(client, order_with, staff_user, product):
    order_with(staff_user, product)
    client.force_login(staff_user)

    page = client.get(product.get_absolute_url()).content.decode()

    assert "Post review" in page


def test_visitors_cannot_review(product):
    assert not Review.objects.can_review(AnonymousUser(), product)
