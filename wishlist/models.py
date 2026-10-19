from django.conf import settings
from django.db import models
from django.utils import timezone

from products.models import Product


class Wishlist(models.Model):
    """A user's saved-for-later list — one per user, created lazily on first touch.

    Independent of the cart: any product can be saved, available or not,
    and buying something never takes it off the list.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist",
    )

    def __str__(self):
        return f"Wishlist for {self.user.username}"

    @classmethod
    def for_user(cls, user):
        """Return the user's wishlist, creating it on first touch."""
        wishlist, _ = cls.objects.get_or_create(user=user)
        return wishlist

    def add(self, product):
        """Save a product; saving it again has no effect."""
        item, _ = self.items.get_or_create(product=product)
        return item

    def remove(self, product):
        """Unsave a product; removing one that isn't saved has no effect."""
        self.items.filter(product=product).delete()

    def contains(self, product):
        return self.items.filter(product=product).exists()

    def lines(self):
        """Items newest first with their products loaded, ready for display."""
        return self.items.select_related("product")


class WishlistItem(models.Model):
    """One saved product; the wishlist–product pair is unique."""

    wishlist = models.ForeignKey(
        Wishlist, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-added_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["wishlist", "product"], name="unique_wishlist_product"
            )
        ]

    def __str__(self):
        return self.product.name
