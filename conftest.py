"""Project-wide pytest fixtures.

Shared test data lives here as plain fixtures — no factories. The suite
grows with the project; tests never invoke the seed command.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from accounts.models import Address
from orders.models import Cart, CartItem
from products.models import Category, Product, Tag


@pytest.fixture
def customer(db):
    return get_user_model().objects.create_user(
        username="customer", password="customer123"
    )


@pytest.fixture
def other_customer(db):
    return get_user_model().objects.create_user(username="other", password="x")


@pytest.fixture
def address(customer):
    """The customer's first address — default shipping and billing."""
    return Address.objects.create(
        user=customer,
        name="Casey Monroe",
        street="214 Synapse Street",
        city="Canyon",
        state="TX",
        zip="79015",
    )


@pytest.fixture
def second_address(customer, address):
    """Saved after ``address``, so it is not a default."""
    return Address.objects.create(
        user=customer,
        name="Casey Monroe",
        street="2600 Neuron Parkway",
        line2="Suite 400",
        city="Amarillo",
        state="TX",
        zip="79101",
    )


@pytest.fixture
def other_address(other_customer):
    return Address.objects.create(
        user=other_customer,
        name="Otto Other",
        street="9 Axon Avenue",
        city="Norman",
        state="OK",
        zip="73019",
    )


@pytest.fixture
def staff_user(db):
    return get_user_model().objects.create_user(
        username="employee",
        password="employee123",
        is_staff=True,
        job_title="Junior Thought Curator",
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Home Assistants", slug="home-assistants")


@pytest.fixture
def product(category):
    return Product.objects.create(
        name="Seraphine Home Hub",
        slug="seraphine-home-hub",
        tagline="She's always listening. In a good way.",
        description="The flagship Seraphine hub with a seven-microphone array.",
        price=Decimal("349.99"),
        category=category,
    )


@pytest.fixture
def unavailable_product(category):
    return Product.objects.create(
        name="EchoPatch",
        slug="echopatch",
        tagline="Never miss a word. Anyone's.",
        price=Decimal("139.00"),
        is_available=False,
        category=category,
    )


@pytest.fixture
def featured_product(category):
    return Product.objects.create(
        name="Seraphine Mini",
        slug="seraphine-mini",
        tagline="All of Seraphine. Less of the counter.",
        price=Decimal("129.99"),
        is_featured=True,
        category=category,
    )


@pytest.fixture
def tag(db):
    return Tag.objects.create(name="bestseller", slug="bestseller")


@pytest.fixture
def cart(customer):
    return Cart.for_user(customer)


@pytest.fixture
def cart_item(cart, product):
    return CartItem.objects.create(cart=cart, product=product, quantity=2)
