from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.templatetags.static import static
from django.urls import reverse

from .images import (
    delete_files_on_commit,
    product_image_path,
    product_original_path,
)

# Categories with a dedicated placeholder illustration; anything else
# falls back to default.svg. A product without an uploaded image shows its
# category's placeholder, a static file.
PLACEHOLDER_CATEGORIES = {
    "home-assistants",
    "neural-implants",
    "neural-wearables",
    "accessories",
    "defense",
    "legacy-products",
}


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("products:category", kwargs={"slug": self.slug})

    @property
    def placeholder_image(self):
        """Static path of the placeholder image shown for this category's products."""
        if self.slug in PLACEHOLDER_CATEGORIES:
            return f"images/placeholders/{self.slug}.svg"
        return "images/placeholders/default.svg"


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        return self.filter(is_available=True)

    def search(self, text):
        """Simple icontains search over name and description."""
        return self.filter(
            models.Q(name__icontains=text) | models.Q(description__icontains=text)
        )


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")
    # Not editable: images only arrive through process_product_image (the
    # back-office form or the seed), never as a raw upload in the admin.
    image = models.ImageField(
        upload_to=product_image_path, max_length=255, blank=True, editable=False
    )
    image_original = models.ImageField(
        upload_to=product_original_path, max_length=255, blank=True, editable=False
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Replaced or removed files go only after the save commits, so a
        # failed save never leaves the product pointing at a deleted file.
        delete_files_on_commit(getattr(self, "_retired_files", []))
        self._retired_files = []

    def get_absolute_url(self):
        return reverse("products:detail", kwargs={"slug": self.slug})

    @property
    def image_url(self):
        """The uploaded image's URL, else the category placeholder's."""
        if self.image:
            return self.image.url
        return static(self.category.placeholder_image)

    def image_files(self):
        """Storage names of this product's image files (processed and original)."""
        return [name for name in (self.image.name, self.image_original.name) if name]

    def set_image(self, processed):
        """Attach a ``ProcessedImage``; it is written to storage on ``save()``."""
        self._retire_current_image()
        self.image = processed.image
        self.image_original = processed.original

    def clear_image(self):
        """Remove the image, so the product shows its placeholder after ``save()``."""
        self._retire_current_image()
        self.image = ""
        self.image_original = ""

    def _retire_current_image(self):
        self._retired_files = [
            *getattr(self, "_retired_files", []),
            *self.image_files(),
        ]


@receiver(post_delete, sender=Product)
def delete_product_image_files(sender, instance, **kwargs):
    """A deleted product's image files go too, once the delete commits.

    A signal rather than ``Product.delete()`` so bulk deletes (the seed's
    wipe, the admin's delete action) clean up as well.
    """
    delete_files_on_commit(instance.image_files())
