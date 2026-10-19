from django.conf import settings
from django.core.validators import (
    MaxLengthValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils import timezone

from products.models import Product

COMMENT_MAX_LENGTH = 2000


class ReviewQuerySet(models.QuerySet):
    def summary(self):
        """The average rating and the review count, in one aggregate query.

        With no reviews the average is ``None`` and the count is 0.
        """
        return self.aggregate(average=models.Avg("rating"), count=models.Count("pk"))


class Review(models.Model):
    """A verified buyer's star rating and comment on one product.

    One review per author per product, enforced by the database. The
    updated timestamp starts equal to the created one, so a review reads
    as edited only once an edit moves it.
    """

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(validators=[MaxLengthValidator(COMMENT_MAX_LENGTH)])
    # A default, not auto_now_add, so the seed can backdate reviews.
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(editable=False)
    edited_by_staff = models.BooleanField(default=False)

    objects = ReviewQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["author", "product"], name="unique_review_author_product"
            )
        ]

    def __str__(self):
        return f"{self.rating}★ {self.product.name} by {self.author.username}"

    def save(self, *args, **kwargs):
        if self.updated_at is None:
            self.updated_at = self.created_at
        super().save(*args, **kwargs)

    @property
    def edit_label(self):
        """``Edited by staff``, ``Edited``, or ``""`` for an untouched review."""
        if self.edited_by_staff:
            return "Edited by staff"
        if self.updated_at != self.created_at:
            return "Edited"
        return ""
