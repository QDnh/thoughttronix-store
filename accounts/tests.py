from http import HTTPStatus

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.db import IntegrityError
from django.urls import reverse

from accounts.forms import AdminAddUserForm
from accounts.models import mask_email

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


def test_navbar_links_to_security_center_when_signed_in(client, customer):
    client.force_login(customer)

    page = client.get(reverse("products:catalog")).content.decode()

    assert reverse("accounts:security") in page


def test_navbar_hides_security_center_from_visitors(client, db):
    page = client.get(reverse("products:catalog")).content.decode()

    assert reverse("accounts:security") not in page


# --- Security Center ----------------------------------------------------------


def test_security_center_requires_login(client, db):
    response = client.get(reverse("accounts:security"))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


@pytest.mark.parametrize("account", ["customer", "staff_user", "admin_user"])
def test_security_center_shows_username_and_email(client, request, account):
    user = request.getfixturevalue(account)
    client.force_login(user)

    response = client.get(reverse("accounts:security"))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert user.username in page
    assert user.email in page
    assert "Change email" in page
    assert "Change password" in page


def test_security_center_links_to_change_email(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert reverse("accounts:change_email") in page


# --- Change email -------------------------------------------------------------


def test_mask_email():
    assert mask_email("casey@example.com") == "c***@example.com"


def test_change_email_requires_login(client, db):
    response = client.get(reverse("accounts:change_email"))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_change_email_page_returns_200(client, customer):
    client.force_login(customer)

    response = client.get(reverse("accounts:change_email"))

    assert response.status_code == HTTPStatus.OK


def test_change_email_saves_lowercased_and_returns_to_hub(client, customer):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:change_email"),
        {"email": "Casey@NewMail.example", "password": "customer123"},
        follow=True,
    )

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    assert "Email updated." in response.content.decode()
    customer.refresh_from_db()
    assert customer.email == "casey@newmail.example"


def test_change_email_notifies_old_address_only(client, customer, mailoutbox):
    client.force_login(customer)

    client.post(
        reverse("accounts:change_email"),
        {"email": "casey@newmail.example", "password": "customer123"},
    )

    assert len(mailoutbox) == 1
    notice = mailoutbox[0]
    assert notice.to == ["customer@example.com"]
    assert notice.from_email == settings.DEFAULT_FROM_EMAIL
    assert "c***@newmail.example" in notice.body
    assert "casey@newmail.example" not in notice.body


def test_change_email_rejects_wrong_password(client, customer, mailoutbox):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:change_email"),
        {"email": "casey@newmail.example", "password": "wrong"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["password"]
    # The typed email is kept so the user only fixes the password.
    assert 'value="casey@newmail.example"' in response.content.decode()
    customer.refresh_from_db()
    assert customer.email == "customer@example.com"
    assert mailoutbox == []


def test_change_email_rejects_email_in_use_regardless_of_case(
    client, customer, other_customer, mailoutbox
):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:change_email"),
        {"email": "Other@Example.com", "password": "customer123"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["email"] == ["That email is already in use."]
    customer.refresh_from_db()
    assert customer.email == "customer@example.com"
    assert mailoutbox == []


def test_change_email_rejects_unchanged_email(client, customer, mailoutbox):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:change_email"),
        {"email": "CUSTOMER@example.com", "password": "customer123"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["email"] == ["That is already your email."]
    assert mailoutbox == []
