from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.functional import cached_property

from products.models import Product

CENT = Decimal("0.01")


class Cart(models.Model):
    """A customer's cart — one per user, created lazily on first touch."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )

    def __str__(self):
        return f"Cart for {self.user.username}"

    @classmethod
    def for_user(cls, user):
        """Return the user's cart, creating it on first touch."""
        cart, _ = cls.objects.get_or_create(user=user)
        return cart

    def add(self, product):
        """Add a product to the cart; a duplicate add increments its line."""
        item, created = self.items.get_or_create(product=product)
        if not created:
            item.quantity += 1
            item.save()
        return item

    def lines(self):
        """Line items with their products loaded, ready for display."""
        return self.items.select_related("product")

    def total(self):
        return sum((item.line_total for item in self.lines()), Decimal("0.00"))

    def item_count(self):
        """Total units across all lines — the navbar badge number."""
        return self.items.aggregate(count=models.Sum("quantity"))["count"] or 0


class CartItem(models.Model):
    """One product line in a cart; the cart–product pair is unique."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"], name="unique_cart_product"
            )
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    @property
    def line_total(self):
        return self.product.price * self.quantity

    def increment(self):
        self.quantity += 1
        self.save()

    def decrement(self):
        """Step the quantity down, stopping at one — removal is explicit."""
        if self.quantity > 1:
            self.quantity -= 1
            self.save()


def normalize_code(text):
    """Codes are case-insensitive and whitespace-trimmed; stored uppercase."""
    return text.strip().upper()


class DiscountCodeQuerySet(models.QuerySet):
    def scheduled(self, now=None):
        return self.filter(starts_at__gt=now or timezone.now())

    def active(self, now=None):
        now = now or timezone.now()
        return self.filter(starts_at__lte=now, expires_at__gt=now)

    def expired(self, now=None):
        return self.filter(expires_at__lte=now or timezone.now())

    def with_order_count(self):
        return self.annotate(order_count=models.Count("orders"))

    def for_checkout(self, text, products, *, now=None):
        """The code named by ``text``, if it can discount these products now.

        The single source of every message a customer sees about a code:
        the Apply button, the checkout form, and ``place_order`` all come
        through here. Raises ``ValidationError`` when the code is unknown,
        not yet active, expired, or matches nothing in ``products``.
        """
        now = now or timezone.now()
        code = self.filter(code=normalize_code(text)).first()
        if code is None:
            raise ValidationError("We don't recognize that code.", code="unknown")
        if code.starts_at > now:
            raise ValidationError(
                f"This code isn't active until {code.starts_display}.",
                code="scheduled",
            )
        if code.expires_at <= now:
            raise ValidationError(
                f"This code expired on {code.expires_display}.", code="expired"
            )
        if not any(code.covers(product) for product in products):
            raise ValidationError(
                f"{code.code} doesn't apply to anything in your cart.",
                code="no_match",
            )
        return code


class DiscountCode(models.Model):
    """A percent-off code for a seasonal promotion.

    Valid from ``starts_at`` up to (not including) ``expires_at``. Either
    order-wide or limited to specific products — ``applies_to`` says which,
    so a forgotten product pick can't silently discount the whole store.
    Orders snapshot what a code gave them; editing or ending a code never
    rewrites a placed order.
    """

    class AppliesTo(models.TextChoices):
        ORDER = "ORDER", "Entire order"
        PRODUCTS = "PRODUCTS", "Specific products"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"

    code = models.CharField(
        max_length=30,
        unique=True,
        validators=[
            RegexValidator(
                r"^[A-Za-z0-9-]+$", "Use only letters, numbers, and hyphens."
            )
        ],
        help_text="What customers type, e.g. SPRING20. Not case-sensitive.",
    )
    percent_off = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="A whole number from 1 to 100.",
    )
    applies_to = models.CharField(
        max_length=8, choices=AppliesTo.choices, default=AppliesTo.ORDER
    )
    products = models.ManyToManyField(
        Product, blank=True, related_name="discount_codes"
    )
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    objects = DiscountCodeQuerySet.as_manager()

    class Meta:
        ordering = ["-starts_at", "code"]

    def __str__(self):
        return self.code

    def clean(self):
        # Either may be missing if its own field already failed validation.
        if self.starts_at and self.expires_at and self.expires_at <= self.starts_at:
            raise ValidationError({"expires_at": "The code must end after it starts."})

    def status(self, now=None):
        now = now or timezone.now()
        if self.starts_at > now:
            return self.Status.SCHEDULED
        if self.expires_at <= now:
            return self.Status.EXPIRED
        return self.Status.ACTIVE

    @property
    def starts_display(self):
        return date_format(timezone.localtime(self.starts_at), "M j, Y")

    @property
    def expires_display(self):
        return date_format(timezone.localtime(self.expires_at), "M j, Y")

    @cached_property
    def _product_ids(self):
        return set(self.products.values_list("pk", flat=True))

    def covers(self, product):
        """Whether this code discounts ``product`` at all."""
        if self.applies_to == self.AppliesTo.ORDER:
            return True
        return product.pk in self._product_ids

    def discount_for(self, product, line_total):
        """Dollars off one line: percent of the line, rounded half-up to cents."""
        if not self.covers(product):
            return Decimal("0.00")
        return (line_total * self.percent_off / 100).quantize(CENT, ROUND_HALF_UP)

    def end_now(self):
        """Retire the code: it expires this instant (a scheduled one never starts)."""
        now = timezone.now()
        self.expires_at = now
        self.starts_at = min(self.starts_at, now)
        self.save(update_fields=["starts_at", "expires_at"])


class Order(models.Model):
    """A placed order — a snapshot, never a live view of the catalog.

    Addresses are flat denormalized fields: the order must not change if
    the customer later edits anything. Of the card, only the last four
    digits survive checkout. A discount is snapshotted the same way — the
    code's text and percent are copied, so editing, ending, or deleting
    the code never changes what this order says it paid.
    """

    class Status(models.TextChoices):
        PLACED = "PLACED", "Placed"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PLACED
    )
    # subtotal − discount_amount = total; without a code the two are equal.
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)
    discount_code = models.ForeignKey(
        DiscountCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    discount_code_text = models.CharField(max_length=30, blank=True)
    discount_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    email = models.EmailField()

    shipping_name = models.CharField(max_length=100)
    shipping_street = models.CharField(max_length=200)
    shipping_line2 = models.CharField(max_length=200, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=2)
    shipping_zip = models.CharField(max_length=10)

    billing_name = models.CharField(max_length=100)
    billing_street = models.CharField(max_length=200)
    billing_line2 = models.CharField(max_length=200, blank=True)
    billing_city = models.CharField(max_length=100)
    billing_state = models.CharField(max_length=2)
    billing_zip = models.CharField(max_length=10)

    card_last4 = models.CharField(max_length=4)

    # default (not auto_now_add) so the seed can backdate orders.
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.number

    @property
    def number(self):
        """The customer-facing order number, e.g. ``TT-2026-00042``."""
        return f"TT-{self.created_at.year}-{self.pk:05d}"


class OrderItem(models.Model):
    """One line of an order, priced as of purchase time.

    Name and unit price are denormalized: order history must not change
    when the catalog does. The product FK survives for linking while the
    product exists.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"

    @property
    def line_total(self):
        """The line before any discount."""
        return self.unit_price * self.quantity

    @property
    def charged(self):
        """What the customer actually paid for this line."""
        return self.line_total - self.discount_amount
