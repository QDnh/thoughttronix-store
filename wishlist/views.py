"""Wishlist views — thin per the architecture convention.

Every endpoint names a *product*, never a wishlist or item id; the
wishlist is always the signed-in user's own, so no request can reach
anyone else's. Add and remove are separate POSTs rather than a toggle,
so a repeated or stale request is harmless.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import TemplateView

from products.models import Product

from .models import Wishlist


class WishlistView(LoginRequiredMixin, TemplateView):
    """The customer's Wishlist page."""

    template_name = "wishlist/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["wishlist"] = Wishlist.for_user(self.request.user)
        return context


class AddToWishlistView(LoginRequiredMixin, View):
    """HTMX: save a product; the product-page button swaps to "saved".

    Looks the product up across the whole catalog, not ``available()`` —
    unlike add-to-cart. Saving isn't buying, so customers may keep
    unavailable products to come back to.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        Wishlist.for_user(request.user).add(product)
        return render(
            request,
            "wishlist/partials/_wishlist_button.html",
            {"product": product, "in_wishlist": True},
        )


class WishlistRemoveView(LoginRequiredMixin, View):
    """Base for HTMX removals: unsave the product, then render a response.

    Subclasses differ only in what they send back.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        wishlist = Wishlist.for_user(request.user)
        wishlist.remove(product)
        return self.respond(request, wishlist, product)

    def respond(self, request, wishlist, product):
        raise NotImplementedError


class RemoveFromWishlistView(WishlistRemoveView):
    """The product-page button swaps back to "not saved"."""

    def respond(self, request, wishlist, product):
        return render(
            request,
            "wishlist/partials/_wishlist_button.html",
            {"product": product, "in_wishlist": False},
        )


class RemoveFromListView(WishlistRemoveView):
    """The Wishlist page's contents swap to the remaining rows."""

    def respond(self, request, wishlist, product):
        return render(
            request,
            "wishlist/partials/_wishlist_contents.html",
            {"wishlist": wishlist},
        )
