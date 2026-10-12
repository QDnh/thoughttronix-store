from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.db import IntegrityError
from django.urls import reverse

from accounts.forms import AdminAddUserForm

# --- Signup -----------------------------------------------------------------


def test_signup_page_returns_200(client, db):
    response = client.get(reverse("accounts:signup"))

    assert response.status_code == HTTPStatus.OK


def test_signup_creates_plain_customer(client, db):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "fresh-thinker",
            "email": "fresh@example.com",
            "password1": "neural-implant-9000",
            "password2": "neural-implant-9000",
        },
        follow=True,
    )

    user = get_user_model().objects.get(username="fresh-thinker")
    assert not user.is_staff
    assert not user.is_superuser

    # Signup hands off to the login page with a confirmation message;
    # auto-login is a student exercise, so the visitor is still anonymous.
    assert response.redirect_chain[-1][0] == reverse("accounts:login")
    assert "Account created" in response.content.decode()
    assert not response.context["user"].is_authenticated


def test_signup_password_mismatch_shows_field_error(client, db):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "fresh-thinker",
            "email": "fresh@example.com",
            "password1": "neural-implant-9000",
            "password2": "neural-implant-9001",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["password2"]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


def test_signup_requires_email(client, db):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "fresh-thinker",
            "password1": "neural-implant-9000",
            "password2": "neural-implant-9000",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["email"]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


def test_signup_rejects_email_in_use_regardless_of_case(client, customer):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "fresh-thinker",
            "email": "Customer@Example.COM",
            "password1": "neural-implant-9000",
            "password2": "neural-implant-9000",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["email"] == ["That email is already in use."]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


def test_signup_stores_email_lowercased(client, db):
    client.post(
        reverse("accounts:signup"),
        {
            "username": "fresh-thinker",
            "email": "Fresh@Example.com",
            "password1": "neural-implant-9000",
            "password2": "neural-implant-9000",
        },
    )

    user = get_user_model().objects.get(username="fresh-thinker")
    assert user.email == "fresh@example.com"


# --- Email on the user model --------------------------------------------------


def test_save_lowercases_email(db):
    user = get_user_model().objects.create_user(
        username="shouty", email="SHOUTY@Example.com", password="x"
    )

    user.refresh_from_db()
    assert user.email == "shouty@example.com"


def test_database_rejects_blank_email(db):
    with pytest.raises(IntegrityError):
        get_user_model().objects.create_user(username="nobody", password="x")


def test_database_rejects_duplicate_email_regardless_of_case(customer):
    with pytest.raises(IntegrityError):
        get_user_model().objects.create_user(
            username="copycat", email="CUSTOMER@example.com", password="x"
        )


def test_createsuperuser_refuses_blank_email(db):
    with pytest.raises(CommandError):
        call_command("createsuperuser", interactive=False, username="boss", email="")

    assert not get_user_model().objects.filter(username="boss").exists()


def test_createsuperuser_stores_email(db):
    call_command(
        "createsuperuser",
        interactive=False,
        username="boss",
        email="Boss@Example.com",
        verbosity=0,
    )

    assert get_user_model().objects.get(username="boss").email == "boss@example.com"


# --- Admin "Add user" ---------------------------------------------------------


ADMIN_ADD_USER = {
    "username": "new-hire",
    "usable_password": "true",
    "password1": "neural-implant-9000",
    "password2": "neural-implant-9000",
}


def test_admin_add_user_form_requires_email(db):
    form = AdminAddUserForm(data=ADMIN_ADD_USER)

    assert not form.is_valid()
    assert form.errors["email"]


def test_admin_add_user_form_rejects_email_in_use_regardless_of_case(customer):
    form = AdminAddUserForm(data={**ADMIN_ADD_USER, "email": "Customer@example.com"})

    assert not form.is_valid()
    assert form.errors["email"] == ["That email is already in use."]


def test_admin_add_user_page_creates_user_with_email(admin_client):
    response = admin_client.post(
        reverse("admin:accounts_user_add"),
        {
            **ADMIN_ADD_USER,
            "email": "New-Hire@example.com",
            # The empty address inline's management form, as a browser sends it.
            "addresses-TOTAL_FORMS": "0",
            "addresses-INITIAL_FORMS": "0",
        },
    )

    assert response.status_code == HTTPStatus.FOUND
    user = get_user_model().objects.get(username="new-hire")
    assert user.email == "new-hire@example.com"


# --- Login and logout --------------------------------------------------------


def test_login_page_returns_200(client, db):
    response = client.get(reverse("accounts:login"))

    assert response.status_code == HTTPStatus.OK


def test_login_round_trip(client, customer):
    response = client.post(
        reverse("accounts:login"),
        {"username": "customer", "password": "customer123"},
        follow=True,
    )

    assert response.redirect_chain[-1][0] == reverse("products:catalog")
    assert response.context["user"] == customer


def test_login_bad_credentials_stays_put(client, customer):
    response = client.post(
        reverse("accounts:login"),
        {"username": "customer", "password": "wrong"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].non_field_errors()


def test_logout_signs_out_with_message(client, customer):
    client.force_login(customer)

    response = client.post(reverse("accounts:logout"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("products:catalog")
    assert "You have signed out." in response.content.decode()
    assert not response.context["user"].is_authenticated


# --- Auth-aware navbar --------------------------------------------------------


def test_navbar_offers_login_and_signup_to_visitors(client, db):
    page = client.get(reverse("products:catalog")).content.decode()

    assert reverse("accounts:login") in page
    assert reverse("accounts:signup") in page
    assert "Sign out" not in page


def test_navbar_greets_signed_in_customer(client, customer):
    client.force_login(customer)

    page = client.get(reverse("products:catalog")).content.decode()

    assert "Hi, customer" in page
    assert "Sign out" in page
    assert reverse("accounts:signup") not in page
