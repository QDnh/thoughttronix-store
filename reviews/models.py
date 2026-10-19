from django.conf import settings
from django.core.validators import (
    MaxLengthValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils import timezone

from orders.models import Order
from products.models import Product

COMMENT_MAX_LENGTH = 2000


class ReviewQuerySet(models.QuerySet):
    def summary(self):
        """The average rating and the review count, in one aggregate query.

        With no reviews the average is ``None`` and the count is 0.
        """
        return self.aggregate(average=models.Avg("rating"), count=models.Count("pk"))

    def pinned_for(self, user):
        """Newest first, with ``user``'s own review (if any) at the top."""
        if not user.is_authenticated:
            return self
        return self.alias(
            is_own=models.Case(
                models.When(author=user, then=1),
                default=0,
                output_field=models.IntegerField(),
            )
        ).order_by("-is_own", "-created_at", "-pk")


class ReviewManager(models.Manager.from_queryset(ReviewQuerySet)):
    def can_review(self, user, product):
        """Whether ``user`` may write a new review of ``product``.

        They must be signed in, have received it (a Delivered order), and
        not have reviewed it yet. Checked only at create time: a later
        status change never touches an existing review.
        """
        if not user.is_authenticated:
            return False
        return (
            Order.objects.has_delivered(user, product)
            and not self.filter(author=user, product=product).exists()
        )

    def own_review(self, user, product):
        """``user``'s review of ``product``, or ``None``."""
        if not user.is_authenticated:
            return None
        return self.filter(author=user, product=product).first()

    def editable_by(self, user):
        """The reviews ``user`` may edit or delete: every one for staff,
        otherwise only their own.

        Views look reviews up through this, so anyone else's review is a
        404, exactly like one that doesn't exist.
        """
        if user.is_staff:
            return self.all()
        return self.filter(author=user)


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

    objects = ReviewManager()

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

    def edit(self, editor, *, comment, rating=None):
        """Save ``editor``'s edit.

        An author may change the rating and the comment, and their edit
        clears the staff flag, so the label always describes the text now
        shown. Anyone else (staff, the only others ``editable_by`` lets
        through) may change only the comment: any ``rating`` is ignored and
        the review is flagged "Edited by staff". Refreshing the updated
        timestamp is what marks the review "Edited".
        """
        if editor.pk == self.author_id:
            self.rating = rating
            self.edited_by_staff = False
        else:
            self.edited_by_staff = True
        self.comment = comment
        self.updated_at = timezone.now()
        self.save()

    @property
    def edit_label(self):
        """``Edited by staff``, ``Edited``, or ``""`` for an untouched review."""
        if self.edited_by_staff:
            return "Edited by staff"
        if self.updated_at != self.created_at:
            return "Edited"
        return ""
