from datetime import UTC, datetime, timedelta

import pytest
from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from .models import COMMENT_MAX_LENGTH, Review

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
