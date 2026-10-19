"""Review views — thin per the architecture convention.

Create names a *product*, like the wishlist's endpoints, and looks it up
across the whole catalog: customers may review a product they received
even after it becomes unavailable. Every response re-renders the whole
reviews section from fresh data, so the page is never partly updated.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, render
from django.views import View

from products.models import Product

from .forms import ReviewForm
from .models import Review

SECTION_TEMPLATE = "reviews/partials/_reviews_section.html"


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
