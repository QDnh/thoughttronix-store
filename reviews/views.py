"""Review views — thin per the architecture convention.

Create names a *product*, like the wishlist's endpoints, and looks it up
across the whole catalog: customers may review a product they received
even after it becomes unavailable. Every other endpoint names a *review*
and finds it through ``editable_by``, so a review the user may not touch
is a 404. Create, update and delete re-render the whole reviews section
from fresh data, so the page is never partly updated; edit and cancel
swap only the one card.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, render
from django.views import View

from products.models import Product

from .forms import ReviewForm
from .models import Review

SECTION_TEMPLATE = "reviews/partials/_reviews_section.html"
CARD_TEMPLATE = "reviews/partials/_review_card.html"


def section_context(user, product, form=None):
    """Everything the reviews section needs, for first load and HTMX alike.

    ``form`` is a bound form to re-show with its errors; otherwise an
    eligible viewer gets a blank one.
    """
    reviews = product.reviews.select_related("author")
    can_review = Review.objects.can_review(user, product)
    return {
        "product": product,
        "reviews": reviews.pinned_for(user),
        "review_summary": reviews.summary(),
        "can_review": can_review,
        "own_review": Review.objects.own_review(user, product),
        "review_form": (form or ReviewForm()) if can_review else None,
    }


class ReviewCreateView(LoginRequiredMixin, View):
    """HTMX: post a review; the whole section swaps in, the new review pinned."""

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        # Re-check on submit: a double-click, a stale tab, or an order no
        # longer Delivered gets the section as it now stands.
        if not Review.objects.can_review(request.user, product):
            return render(
                request, SECTION_TEMPLATE, section_context(request.user, product)
            )
        form = ReviewForm(request.POST)
        if form.is_valid():
            form.instance.author = request.user
            form.instance.product = product
            try:
                with transaction.atomic():
                    form.save()
            except IntegrityError:
                pass  # A simultaneous submit saved first; show that review.
            form = None
        return render(
            request, SECTION_TEMPLATE, section_context(request.user, product, form)
        )


def edit_form(review, editor, data=None):
    """``editor``'s edit form for ``review``, its ids unique to this card.

    Unique ids keep its labels pointing at its own fields when another
    form (a new review, another card being edited) is on the page. Staff
    editing someone else's review get the comment only.
    """
    return ReviewForm(
        data, instance=review, editor=editor, auto_id=f"id_review_{review.pk}_%s"
    )


class EditableReviewMixin(LoginRequiredMixin):
    """Finds the URL's review among those the user may edit, or 404s."""

    def get_review(self):
        reviews = Review.objects.editable_by(self.request.user)
        return get_object_or_404(
            reviews.select_related("author", "product"), pk=self.kwargs["pk"]
        )


class ReviewEditView(EditableReviewMixin, View):
    """HTMX: swap one card into edit mode, pre-filled."""

    def get(self, request, pk):
        review = self.get_review()
        return render(
            request,
            CARD_TEMPLATE,
            {"review": review, "edit_form": edit_form(review, request.user)},
        )


class ReviewCancelView(EditableReviewMixin, View):
    """HTMX: swap one card back to display mode, unchanged."""

    def get(self, request, pk):
        return render(request, CARD_TEMPLATE, {"review": self.get_review()})


class ReviewUpdateView(EditableReviewMixin, View):
    """HTMX: save an edit; the whole section swaps in.

    An invalid edit sends back just the card, still in edit mode with its
    errors, retargeted onto the card so the rest of the page stays put.
    """

    def post(self, request, pk):
        review = self.get_review()
        form = edit_form(review, request.user, request.POST)
        if not form.is_valid():
            response = render(
                request, CARD_TEMPLATE, {"review": review, "edit_form": form}
            )
            response["HX-Retarget"] = f"#review-{review.pk}"
            return response
        review.edit(request.user, **form.cleaned_data)
        return render(
            request, SECTION_TEMPLATE, section_context(request.user, review.product)
        )


class ReviewDeleteView(EditableReviewMixin, View):
    """HTMX: delete a review; the whole section swaps in.

    An author who still has a delivered purchase gets the form back.
    """

    def post(self, request, pk):
        review = self.get_review()
        review.delete()
        return render(
            request, SECTION_TEMPLATE, section_context(request.user, review.product)
        )
