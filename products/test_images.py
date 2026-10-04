"""Product images: processing, plain-language validation, the back-office
upload round-trip, file cleanup, display fallback, and the seed's photos."""

import logging
from io import BytesIO
from pathlib import Path

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from PIL import Image, ImageOps

from .forms import IMAGE_NOT_SAVED
from .images import (
    COULD_NOT_PROCESS,
    IMAGE_SIZE,
    MAX_UPLOAD_BYTES,
    process_product_image,
)
from .models import Product
from .test_backoffice import product_data

pytestmark = pytest.mark.django_db


def make_upload(size=IMAGE_SIZE, image_format="PNG", name="photo.png"):
    """An in-memory picture, uploaded as if from a browser."""
    buffer = BytesIO()
    Image.new("RGB", size, "teal").save(buffer, image_format)
    return SimpleUploadedFile(name, buffer.getvalue())


def post_product(client, product, **extra):
    """POST the edit form for ``product``, with its current text fields."""
    data = product_data(product.category, name=product.name, slug=product.slug)
    data.update(extra)
    return client.post(
        reverse("products:manage_product_update", kwargs={"pk": product.pk}), data
    )


def error_on_upload(client, upload, category):
    """POST a new product with ``upload`` and return the page text."""
    response = client.post(
        reverse("products:manage_product_create"),
        product_data(category, image=upload),
    )
    assert not Product.objects.exists()
    return response.content.decode()


@pytest.fixture
def product_with_image(product):
    product.set_image(process_product_image(make_upload()))
    product.save()
    return product


@pytest.fixture
def staff_client(client, staff_user):
    client.force_login(staff_user)
    return client


# --- Processing ------------------------------------------------------------


def test_upload_is_cropped_to_4_5_webp_and_original_kept(product):
    upload = make_upload(size=(1600, 1000))

    product.set_image(process_product_image(upload))
    product.save()

    assert product.image.name.startswith("products/seraphine-home-hub-")
    assert product.image.name.endswith(".webp")
    with Image.open(product.image.path) as stored:
        assert stored.format == "WEBP"
        assert stored.size == IMAGE_SIZE
    assert product.image_original.name.startswith("products/originals/")
    assert product.image_original.name.endswith(".png")
    upload.seek(0)
    assert Path(product.image_original.path).read_bytes() == upload.read()


def test_every_upload_gets_a_new_name(product):
    product.set_image(process_product_image(make_upload()))
    product.save()
    first = product.image.name

    product.set_image(process_product_image(make_upload()))
    product.save()

    assert product.image.name != first


def test_jpeg_and_webp_are_accepted():
    for image_format in ("JPEG", "WEBP"):
        processed = process_product_image(make_upload(image_format=image_format))
        assert processed.image.size > 0


# --- Validation messages ----------------------------------------------------


def test_non_image_file_is_rejected_plainly(staff_client, category):
    upload = SimpleUploadedFile("notes.txt", b"not a picture at all")

    page = error_on_upload(staff_client, upload, category)

    assert "This file isn&#x27;t an image we can read." in page


def test_svg_is_rejected(staff_client, category):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000"/>'

    page = error_on_upload(staff_client, SimpleUploadedFile("logo.svg", svg), category)

    assert "Please upload a JPEG, PNG, or WebP picture." in page


def test_other_image_formats_are_rejected(staff_client, category):
    upload = make_upload(image_format="GIF", name="photo.gif")

    page = error_on_upload(staff_client, upload, category)

    assert "Please upload a JPEG, PNG, or WebP picture." in page


def test_oversized_file_is_rejected_with_its_size(staff_client, category):
    upload = SimpleUploadedFile("huge.png", b"0" * (MAX_UPLOAD_BYTES + 100_000))

    page = error_on_upload(staff_client, upload, category)

    assert "This image is too large (10.1 MB)." in page
    assert "Please upload one smaller than 10 MB." in page


def test_small_image_is_rejected_with_its_dimensions(staff_client, category):
    page = error_on_upload(staff_client, make_upload(size=(640, 480)), category)

    assert "This image is too small (640 × 480 pixels)." in page
    assert "at least 800 × 1000 pixels" in page


def test_decompression_bomb_counts_as_too_large(staff_client, category, monkeypatch):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)

    page = error_on_upload(staff_client, make_upload(), category)

    assert "This image is too large." in page


def test_unexpected_failure_is_plain_and_logged(
    staff_client, category, monkeypatch, caplog
):
    def explode(*args, **kwargs):
        raise RuntimeError("codec exploded")

    monkeypatch.setattr(ImageOps, "fit", explode)

    with caplog.at_level(logging.ERROR, logger="products.images"):
        page = error_on_upload(staff_client, make_upload(), category)

    assert COULD_NOT_PROCESS.replace("'", "&#x27;") in page
    assert "codec exploded" not in page
    assert "codec exploded" in caplog.text


# --- The back-office form ---------------------------------------------------


def test_product_form_uploads_files(staff_client):
    """Without multipart encoding, browsers silently drop the file."""
    page = staff_client.get(reverse("products:manage_product_create")).content.decode()

    assert 'enctype="multipart/form-data"' in page
    assert 'type="file"' in page
    assert "file-input file-input-primary" in page  # styled as a button


def test_staff_can_upload_an_image(staff_client, category):
    staff_client.post(
        reverse("products:manage_product_create"),
        product_data(category, image=make_upload()),
    )

    product = Product.objects.get(slug="mindsync-sleep-halo")
    assert product.image
    assert default_storage.exists(product.image.name)
    assert default_storage.exists(product.image_original.name)


def test_other_errors_save_nothing_and_ask_for_the_file_again(
    staff_client, category, media_root
):
    response = staff_client.post(
        reverse("products:manage_product_create"),
        product_data(category, price="-1", image=make_upload()),
    )

    page = response.content.decode()
    assert "Your image wasn&#x27;t saved. Please choose the file again." in page
    assert 'value="MindSync Sleep Halo"' in page  # text fields re-fill
    assert not Product.objects.exists()
    assert not media_root.exists() or not any(media_root.rglob("*.*"))


def test_failed_edit_keeps_the_current_image(staff_client, product_with_image):
    current = product_with_image.image.name

    response = post_product(
        staff_client, product_with_image, name="", image=make_upload()
    )

    assert IMAGE_NOT_SAVED.replace("'", "&#x27;") in response.content.decode()
    product_with_image.refresh_from_db()
    assert product_with_image.image.name == current


def test_edit_form_previews_the_current_image(staff_client, product_with_image):
    page = staff_client.get(
        reverse("products:manage_product_update", kwargs={"pk": product_with_image.pk})
    ).content.decode()

    assert product_with_image.image.url in page
    assert "Remove image (show the placeholder instead)" in page


def test_remove_checkbox_restores_the_placeholder(
    staff_client, product_with_image, django_capture_on_commit_callbacks
):
    old_files = product_with_image.image_files()

    with django_capture_on_commit_callbacks(execute=True):
        post_product(staff_client, product_with_image, **{"image-clear": "on"})

    product_with_image.refresh_from_db()
    assert not product_with_image.image
    assert not product_with_image.image_original
    assert not any(default_storage.exists(name) for name in old_files)


def test_remove_and_new_file_together_is_an_error(staff_client, product_with_image):
    current = product_with_image.image.name

    response = post_product(
        staff_client, product_with_image, image=make_upload(), **{"image-clear": "on"}
    )

    assert "not both" in response.content.decode()
    product_with_image.refresh_from_db()
    assert product_with_image.image.name == current


def test_replacing_deletes_the_old_files_after_commit(
    staff_client, product_with_image, django_capture_on_commit_callbacks
):
    old_files = product_with_image.image_files()

    with django_capture_on_commit_callbacks(execute=True):
        post_product(staff_client, product_with_image, image=make_upload())

    product_with_image.refresh_from_db()
    assert product_with_image.image.name not in old_files
    assert default_storage.exists(product_with_image.image.name)
    assert not any(default_storage.exists(name) for name in old_files)


def test_old_files_stay_until_the_save_commits(staff_client, product_with_image):
    """No commit (the test's transaction never ends), so nothing is deleted."""
    old_files = product_with_image.image_files()

    post_product(staff_client, product_with_image, image=make_upload())

    assert all(default_storage.exists(name) for name in old_files)


def test_deleting_a_product_deletes_its_files(
    staff_client, product_with_image, django_capture_on_commit_callbacks
):
    files = product_with_image.image_files()

    with django_capture_on_commit_callbacks(execute=True):
        staff_client.post(
            reverse(
                "products:manage_product_delete", kwargs={"pk": product_with_image.pk}
            )
        )

    assert not any(default_storage.exists(name) for name in files)


# --- Display ---------------------------------------------------------------


def test_image_url_falls_back_to_the_category_placeholder(product):
    assert product.image_url == "/static/images/placeholders/home-assistants.svg"


def test_image_url_is_the_upload_when_there_is_one(product_with_image):
    assert product_with_image.image_url == product_with_image.image.url
    assert product_with_image.image_url.startswith("/media/products/")


def test_catalog_and_detail_show_the_uploaded_image(client, product_with_image):
    for url in (reverse("products:catalog"), product_with_image.get_absolute_url()):
        page = client.get(url).content.decode()

        assert f'src="{product_with_image.image.url}"' in page
        assert 'loading="lazy"' in page
        # A missing file swaps to the placeholder rather than showing broken.
        assert "placeholders/home-assistants.svg" in page


def test_catalog_shows_the_placeholder_without_an_image(client, product):
    page = client.get(reverse("products:catalog")).content.decode()

    assert 'src="/static/images/placeholders/home-assistants.svg"' in page


# --- The seed ---------------------------------------------------------------


def test_seed_attaches_product_photos():
    call_command("seed")

    with_images = Product.objects.exclude(image="")
    assert with_images.count() == 12
    seraphine = Product.objects.get(slug="seraphine")
    assert seraphine.image.name.endswith(".webp")
    assert default_storage.exists(seraphine.image.name)
    assert default_storage.exists(seraphine.image_original.name)
    assert not Product.objects.get(slug="seraphine-mini").image
    assert Product.objects.get(slug="soulsear-tactical-core").image
    assert not Product.objects.get(slug="soulsear-mark-i").image


def test_reseeding_clears_the_old_files(django_capture_on_commit_callbacks):
    call_command("seed")
    old_files = Product.objects.get(slug="seraphine").image_files()

    with django_capture_on_commit_callbacks(execute=True):
        call_command("seed")

    assert not any(default_storage.exists(name) for name in old_files)
