import re
from datetime import datetime, timedelta
from http import HTTPStatus

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.management import CommandError, call_command
from django.db import IntegrityError
from django.test import Client
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


# --- Change password ----------------------------------------------------------


def test_security_center_links_to_change_password(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert reverse("accounts:password_change") in page


def test_change_password_requires_login(client, db):
    response = client.get(reverse("accounts:password_change"))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_change_password_page_returns_200(client, customer):
    client.force_login(customer)

    response = client.get(reverse("accounts:password_change"))

    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.context["form"], PasswordChangeForm)


def test_change_password_saves_and_returns_to_hub(client, customer):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:password_change"),
        {
            "old_password": "customer123",
            "new_password1": "fresh-Synapse-42",
            "new_password2": "fresh-Synapse-42",
        },
        follow=True,
    )

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    assert "Password updated." in response.content.decode()
    customer.refresh_from_db()
    assert customer.check_password("fresh-Synapse-42")


def test_change_password_keeps_this_session_and_ends_others(client, customer):
    other_device = Client()
    other_device.force_login(customer)
    client.force_login(customer)

    client.post(
        reverse("accounts:password_change"),
        {
            "old_password": "customer123",
            "new_password1": "fresh-Synapse-42",
            "new_password2": "fresh-Synapse-42",
        },
    )

    security = reverse("accounts:security")
    assert client.get(security).status_code == HTTPStatus.OK
    assert other_device.get(security).status_code == HTTPStatus.FOUND


def test_change_password_notifies_account_email(client, customer, mailoutbox):
    client.force_login(customer)

    client.post(
        reverse("accounts:password_change"),
        {
            "old_password": "customer123",
            "new_password1": "fresh-Synapse-42",
            "new_password2": "fresh-Synapse-42",
        },
    )

    assert len(mailoutbox) == 1
    notice = mailoutbox[0]
    assert notice.to == ["customer@example.com"]
    assert notice.from_email == settings.DEFAULT_FROM_EMAIL
    assert notice.subject == "Your ThoughtTronix password was changed"
    assert "customer" in notice.body
    assert "fresh-Synapse-42" not in notice.body


@pytest.mark.parametrize(
    ("data", "field"),
    [
        (
            {
                "old_password": "wrong",
                "new_password1": "fresh-Synapse-42",
                "new_password2": "fresh-Synapse-42",
            },
            "old_password",
        ),
        (
            {
                "old_password": "customer123",
                "new_password1": "fresh-Synapse-42",
                "new_password2": "fresh-Synapse-43",
            },
            "new_password2",
        ),
        (
            {
                "old_password": "customer123",
                "new_password1": "password",
                "new_password2": "password",
            },
            "new_password2",
        ),
    ],
    ids=["wrong-old-password", "mismatch", "weak"],
)
def test_change_password_rejects_bad_input(client, customer, mailoutbox, data, field):
    client.force_login(customer)

    response = client.post(reverse("accounts:password_change"), data)

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors[field]
    assert "text-error" in response.content.decode()
    customer.refresh_from_db()
    assert customer.check_password("customer123")
    assert mailoutbox == []


def test_setting_a_password_elsewhere_sends_no_notice(client, db, mailoutbox):
    """``set_password`` isn't overridden: signup and create_user stay silent."""
    get_user_model().objects.create_user(
        username="quiet", email="quiet@example.com", password="x"
    )
    client.post(
        reverse("accounts:signup"),
        {
            "username": "newbie",
            "email": "newbie@example.com",
            "password1": "fresh-Synapse-42",
            "password2": "fresh-Synapse-42",
        },
    )

    assert get_user_model().objects.filter(username="newbie").exists()
    assert mailoutbox == []


# --- Forgot password: request and email ---------------------------------------


RESET_LINK = re.compile(r"https?://testserver(/accounts/password-reset/\S+/\S+/)")


def test_login_page_links_to_forgot_password(client, db):
    page = client.get(reverse("accounts:login")).content.decode()

    assert "Forgot password?" in page
    assert reverse("accounts:password_reset") in page


def test_password_reset_page_returns_200(client, db):
    response = client.get(reverse("accounts:password_reset"))

    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.context["form"], PasswordResetForm)


def test_password_reset_timeout_is_one_hour():
    assert settings.PASSWORD_RESET_TIMEOUT == 3600


def test_password_reset_emails_link_and_username(client, customer, mailoutbox):
    response = client.post(
        reverse("accounts:password_reset"), {"email": "customer@example.com"}
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("accounts:password_reset_done")
    assert len(mailoutbox) == 1
    message = mailoutbox[0]
    assert message.to == ["customer@example.com"]
    assert message.from_email == settings.DEFAULT_FROM_EMAIL
    assert message.subject == "Reset your ThoughtTronix password"
    assert "Your username is: customer" in message.body


def test_password_reset_link_reaches_confirm_page(client, customer, mailoutbox):
    client.post(reverse("accounts:password_reset"), {"email": "customer@example.com"})

    link = RESET_LINK.search(mailoutbox[0].body).group(1)
    response = client.get(link, follow=True)

    # Django swaps the token into the session and redirects to a token-free
    # URL; a valid link lands there with ``validlink`` set.
    assert response.status_code == HTTPStatus.OK
    assert response.context["validlink"]


def test_password_reset_lookup_ignores_case(client, customer, mailoutbox):
    client.post(reverse("accounts:password_reset"), {"email": "CUSTOMER@Example.com"})

    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["customer@example.com"]


def test_password_reset_unknown_email_gets_same_response(client, customer, mailoutbox):
    known = client.post(
        reverse("accounts:password_reset"), {"email": "customer@example.com"}
    )
    mailoutbox.clear()

    unknown = client.post(
        reverse("accounts:password_reset"), {"email": "stranger@example.com"}
    )

    assert unknown.status_code == known.status_code == HTTPStatus.FOUND
    assert unknown.url == known.url == reverse("accounts:password_reset_done")
    assert mailoutbox == []


def test_password_reset_skips_unusable_password(client, db, mailoutbox):
    background = get_user_model().objects.create_user(
        username="background", email="background@example.com"
    )
    assert not background.has_usable_password()

    response = client.post(
        reverse("accounts:password_reset"), {"email": "background@example.com"}
    )

    assert response.url == reverse("accounts:password_reset_done")
    assert mailoutbox == []


def test_password_reset_done_page_is_noncommittal(client, db):
    page = client.get(reverse("accounts:password_reset_done")).content.decode()

    assert "If that email belongs to a ThoughtTronix account" in page


# --- Forgot password: set a new password --------------------------------------


NEW_PASSWORD = "fresh-Synapse-42"


def open_reset_link(client, mailoutbox):
    """Request a reset for the customer and follow the emailed link.

    Returns the response for the token-free ``set-password`` page that
    Django redirects to.
    """
    client.post(reverse("accounts:password_reset"), {"email": "customer@example.com"})
    link = RESET_LINK.search(mailoutbox[-1].body).group(1)
    return client.get(link, follow=True)


def set_new_password(client, page, password=NEW_PASSWORD):
    url = page.redirect_chain[-1][0]
    return client.post(
        url, {"new_password1": password, "new_password2": password}, follow=True
    )


def test_password_reset_confirm_uses_stock_form(client, customer, mailoutbox):
    page = open_reset_link(client, mailoutbox)

    assert isinstance(page.context["form"], SetPasswordForm)
    assert "old_password" not in page.context["form"].fields


def test_password_reset_sets_password_and_lands_on_login(client, customer, mailoutbox):
    page = open_reset_link(client, mailoutbox)

    response = set_new_password(client, page)

    assert response.redirect_chain[-1][0] == reverse("accounts:login")
    assert "Password reset" in response.content.decode()
    customer.refresh_from_db()
    assert customer.check_password(NEW_PASSWORD)
    assert Client().login(username="customer", password=NEW_PASSWORD)


def test_password_reset_does_not_sign_in(client, customer, mailoutbox):
    page = open_reset_link(client, mailoutbox)

    set_new_password(client, page)

    assert "_auth_user_id" not in client.session


def test_password_reset_notifies_account_email(client, customer, mailoutbox):
    page = open_reset_link(client, mailoutbox)
    mailoutbox.clear()

    set_new_password(client, page)

    assert len(mailoutbox) == 1
    notice = mailoutbox[0]
    assert notice.to == ["customer@example.com"]
    assert "password on your ThoughtTronix account was just changed" in notice.body


def test_password_reset_enforces_password_validators(client, customer, mailoutbox):
    page = open_reset_link(client, mailoutbox)
    mailoutbox.clear()

    response = set_new_password(client, page, password="password")

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["new_password2"]
    customer.refresh_from_db()
    assert customer.check_password("customer123")
    assert mailoutbox == []


def test_password_reset_complete_redirects_to_login_silently(client, db):
    response = client.get(reverse("accounts:password_reset_complete"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("accounts:login")
    assert "Password reset" not in response.content.decode()


def assert_link_rejected(page):
    assert page.status_code == HTTPStatus.OK
    assert not page.context["validlink"]
    content = page.content.decode()
    assert "invalid or has expired" in content
    assert reverse("accounts:password_reset") in content


def test_password_reset_link_rejected_after_one_hour(
    client, customer, mailoutbox, monkeypatch
):
    client.post(reverse("accounts:password_reset"), {"email": "customer@example.com"})
    link = RESET_LINK.search(mailoutbox[0].body).group(1)
    later = datetime.now() + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT + 1)
    monkeypatch.setattr(PasswordResetTokenGenerator, "_now", lambda self: later)

    assert_link_rejected(client.get(link, follow=True))


def test_password_reset_link_rejected_after_use(client, customer, mailoutbox):
    client.post(reverse("accounts:password_reset"), {"email": "customer@example.com"})
    link = RESET_LINK.search(mailoutbox[0].body).group(1)
    set_new_password(client, client.get(link, follow=True))

    assert_link_rejected(client.get(link, follow=True))


def test_password_reset_link_rejected_after_password_change(
    client, customer, mailoutbox
):
    client.post(reverse("accounts:password_reset"), {"email": "customer@example.com"})
    link = RESET_LINK.search(mailoutbox[0].body).group(1)
    customer.set_password("another-Synapse-42")
    customer.save()

    assert_link_rejected(client.get(link, follow=True))


def test_password_reset_link_rejected_after_email_change(client, customer, mailoutbox):
    client.post(reverse("accounts:password_reset"), {"email": "customer@example.com"})
    link = RESET_LINK.search(mailoutbox[0].body).group(1)
    customer.change_email("moved@example.com")

    assert_link_rejected(client.get(link, follow=True))


def test_password_reset_garbage_link_rejected(client, db):
    url = reverse(
        "accounts:password_reset_confirm",
        kwargs={"uidb64": "MQ", "token": "not-a-token"},
    )

    assert_link_rejected(client.get(url, follow=True))
