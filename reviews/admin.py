from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """A support fallback; staff moderate on the product page."""

    list_display = ("product", "author", "rating", "created_at", "edited_by_staff")
    list_filter = ("rating", "edited_by_staff")
    search_fields = ("product__name", "author__username", "comment")
    readonly_fields = ("updated_at",)
