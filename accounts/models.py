from collections.abc import Mapping
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction

from .validators import US_STATES, zip_validator


class User(AbstractUser):
    """The store's user model.

    Roles use Django's own vocabulary and nothing else: customers are
    plain users, employees are ``is_staff``, the admin is ``is_superuser``.
    """

    # Nullable per the PRD: an absent job title is unknown, not empty.
    job_title = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001


class AddressManager(models.Manager):
    def save_from_checkout(
        self, user: AbstractUser, data: Mapping[str, Any], *, prefix: str
    ) -> "Address":
        """Save one checkout address section to the user's address book.

        ``data`` is a valid ``CheckoutForm``'s ``cleaned_data``; ``prefix``
        picks the section (``"shipping_"`` or ``"billing_"``). An exact
        match of an address already saved is returned as-is — reusing a
        saved address at checkout never creates a duplicate.
        """
        values = {field: data[f"{prefix}{field}"] for field in Address.FIELDS}
        address, _ = self.get_or_create(user=user, **values)
        return address


class Address(models.Model):
    """A saved address, usable for shipping or billing alike.

    The location fields mirror ``Order``'s ``shipping_*``/``billing_*``
    fields exactly, so any saved address fits onto an order. Orders copy
    the values — editing or deleting an address never touches history.
    """

    FIELDS = ["name", "street", "line2", "city", "state", "zip"]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    name = models.CharField("Full name", max_length=100)
    street = models.CharField("Street address", max_length=200)
    line2 = models.CharField("Apt, suite, etc. (optional)", max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2, choices=US_STATES)
    zip = models.CharField("ZIP code", max_length=10, validators=[zip_validator])

    is_default_shipping = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)

    objects = AddressManager()

    class Meta:
        verbose_name_plural = "addresses"
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default_shipping=True),
                name="one_default_shipping_address_per_user",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default_billing=True),
                name="one_default_billing_address_per_user",
            ),
        ]

    def __str__(self):
        street = f"{self.street}, {self.line2}" if self.line2 else self.street
        return f"{self.name} — {street}, {self.city}, {self.state} {self.zip}"

    def save(self, *args, **kwargs):
        """A new address fills any empty default slot — never replaces one."""
        if self._state.adding:
            siblings = Address.objects.filter(user_id=self.user_id)
            if not siblings.filter(is_default_shipping=True).exists():
                self.is_default_shipping = True
            if not siblings.filter(is_default_billing=True).exists():
                self.is_default_billing = True
        super().save(*args, **kwargs)

    def make_default_shipping(self):
        self._make_default("is_default_shipping")

    def make_default_billing(self):
        self._make_default("is_default_billing")

    @transaction.atomic
    def _make_default(self, flag):
        # Clear the old default first, or the constraint would see two.
        self.user.addresses.exclude(pk=self.pk).filter(**{flag: True}).update(
            **{flag: False}
        )
        setattr(self, flag, True)
        self.save(update_fields=[flag])

    def as_checkout_initial(self, prefix):
        """This address as ``CheckoutForm`` initial data for one section."""
        return {f"{prefix}{field}": getattr(self, field) for field in self.FIELDS}
