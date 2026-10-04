"""Back-office forms for the catalog models.

ModelForms inherit the models' own rules (name required, slug unique);
the explicit ``price`` declaration adds the one rule the model doesn't
carry — the price must be positive. Widgets get their DaisyUI classes
in one shared ``__init__`` loop, as on ``CheckoutForm``.

``ProductForm`` also takes the product image. It is all-or-nothing: if any
field has an error, nothing is saved and the product keeps its current image.
"""

from decimal import Decimal

from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from .images import IMAGE_SIZE, MAX_UPLOAD_MB, process_product_image
from .models import Category, Product, Tag

IMAGE_NOT_SAVED = "Your image wasn't saved. Please choose the file again."


class StyledModelForm(forms.ModelForm):
    """Base form that dresses every widget in DaisyUI classes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "toggle toggle-primary"
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "textarea w-full"
                widget.attrs.setdefault("rows", 6)
            elif isinstance(widget, forms.SelectMultiple):
                # `block` undoes DaisyUI's inline-flex, which would lay the
                # options out side by side instead of as a stacked list.
                widget.attrs["class"] = "select block h-auto w-full"
                widget.attrs.setdefault("size", 8)
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            elif isinstance(widget, forms.FileInput):
                # The color modifier makes "Choose file" read as a button;
                # the default grey all but vanishes on the night theme.
                widget.attrs["class"] = "file-input file-input-primary w-full"
            else:
                widget.attrs["class"] = "input w-full"


class ProductImageInput(forms.ClearableFileInput):
    clear_checkbox_label = "Remove image (show the placeholder instead)"


class ProductForm(StyledModelForm):
    price = forms.DecimalField(
        label="Price (USD)",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    # Not a model field on the form: the upload is processed in clean_image
    # and attached in save(). The widget's "clear" checkbox is rendered by
    # products/partials/_image_field.html, beside a preview of the image.
    image = forms.FileField(
        label="Product image",
        required=False,
        widget=ProductImageInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        help_text=(
            f"JPEG, PNG, or WebP, at least {IMAGE_SIZE[0]} × {IMAGE_SIZE[1]} "
            f"pixels and under {MAX_UPLOAD_MB} MB. It is cropped to fit the catalog."
        ),
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "slug",
            "tagline",
            "description",
            "price",
            "category",
            "tags",
            "is_available",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processed_image = None

    def clean_image(self):
        image = self.cleaned_data["image"]
        # None = no file chosen, False = "remove" ticked; only a new upload
        # needs checking.
        if isinstance(image, UploadedFile):
            self.processed_image = process_product_image(image)
        return image

    def full_clean(self):
        super().full_clean()
        # The chosen image was fine but another field wasn't. Browsers can't
        # re-fill a file input, so say plainly that it needs choosing again.
        if self._errors and self.processed_image:
            self.add_error("image", IMAGE_NOT_SAVED)

    def save(self, commit=True):
        if self.processed_image:
            self.instance.set_image(self.processed_image)
        elif self.cleaned_data["image"] is False:
            self.instance.clear_image()
        with transaction.atomic():
            return super().save(commit)


class CategoryForm(StyledModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug"]


class TagForm(StyledModelForm):
    class Meta:
        model = Tag
        fields = ["name", "slug"]
