"""Product images: validate an upload once, then crop it to the catalog's shape.

Every product image is stored twice: the exact upload (``image_original``,
kept so new sizes or crops can be made later without re-uploading) and one
processed WebP (``image``, the only file the site serves). The back-office
form and the ``seed`` command both go through ``process_product_image``.

Every error a staff member can see is plain language — never technical text.
"""

import logging
import math
import secrets
import warnings
from io import BytesIO
from pathlib import Path
from typing import NamedTuple

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

# The one processed size. Its 4:5 shape is the catalog frame, and it doubles
# as the minimum upload size so no image is ever stretched. Change it here.
IMAGE_SIZE = (800, 1000)
MAX_UPLOAD_MB = 10
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Pillow's format name -> the extension the stored original gets.
ACCEPTED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}

UNREADABLE = (
    "This file isn't an image we can read. Please upload a JPEG, PNG, or WebP picture."
)
TOO_LARGE = (
    "This image is too large{detail}. "
    f"Please upload one smaller than {MAX_UPLOAD_MB} MB."
)
TOO_SMALL = (
    "This image is too small ({width} × {height} pixels). "
    f"Please upload one at least {IMAGE_SIZE[0]} × {IMAGE_SIZE[1]} pixels "
    "so it looks sharp on the site."
)
COULD_NOT_PROCESS = (
    "We couldn't process this image. Please try saving it again as a JPEG "
    "or PNG, or try a different picture."
)


class ProcessedImage(NamedTuple):
    """An upload that passed validation, ready to attach to a product."""

    image: ContentFile
    original: ContentFile


def process_product_image(upload) -> ProcessedImage:
    """Validate an uploaded image and crop it to the catalog's shape.

    Accepts any Django ``File`` (an upload, or an opened file in the seed).
    Returns the processed WebP and the untouched original. Raises
    ``ValidationError`` with a plain-language message when the file can't
    be used; an unexpected failure is logged and reported the same way.
    """
    if upload.size > MAX_UPLOAD_BYTES:
        # Round up, so a file just over the limit never reads "10.0 MB".
        size_mb = math.ceil(upload.size / (1024 * 1024) * 10) / 10
        raise ValidationError(
            TOO_LARGE.format(detail=f" ({size_mb} MB)"), code="too_large"
        )

    upload.seek(0)
    data = upload.read()
    try:
        # Pillow warns, then errors, on images with absurd pixel counts
        # (decompression bombs); treat both as "too large".
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as opened:
                image_format = opened.format
                if image_format not in ACCEPTED_FORMATS:
                    raise ValidationError(UNREADABLE, code="unreadable")
                # Phone photos store their rotation separately; apply it first.
                picture = ImageOps.exif_transpose(opened)
        if picture.width < IMAGE_SIZE[0] or picture.height < IMAGE_SIZE[1]:
            raise ValidationError(
                TOO_SMALL.format(width=picture.width, height=picture.height),
                code="too_small",
            )
        has_alpha = "A" in picture.getbands() or "transparency" in picture.info
        picture = picture.convert("RGBA" if has_alpha else "RGB")
        fitted = ImageOps.fit(picture, IMAGE_SIZE, Image.Resampling.LANCZOS)
        output = BytesIO()
        fitted.save(output, "WEBP", quality=82)
    except ValidationError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError(TOO_LARGE.format(detail=""), code="too_large") from None
    except UnidentifiedImageError:
        raise ValidationError(UNREADABLE, code="unreadable") from None
    except Exception:
        logger.exception("Could not process product image %r", upload.name)
        raise ValidationError(COULD_NOT_PROCESS, code="could_not_process") from None

    return ProcessedImage(
        image=ContentFile(output.getvalue(), name="image.webp"),
        original=ContentFile(data, name=f"original{ACCEPTED_FORMATS[image_format]}"),
    )


def _stored_name(instance, folder, extension):
    """A fresh name on every upload, so browsers never show a stale cached image."""
    return f"{folder}/{instance.slug[:80]}-{secrets.token_hex(4)}{extension}"


def product_image_path(instance, filename):
    """``upload_to`` for the processed image: ``products/<slug>-<random>.webp``."""
    return _stored_name(instance, "products", ".webp")


def product_original_path(instance, filename):
    """``upload_to`` for the original: ``products/originals/<slug>-<random>.<ext>``."""
    return _stored_name(instance, "products/originals", Path(filename).suffix.lower())


def delete_files_on_commit(names):
    """Delete stored files, but only once the current transaction commits.

    If the save that replaced them rolls back, the files are still needed.
    """
    for name in names:
        if name:
            transaction.on_commit(
                lambda name=name: default_storage.delete(name), robust=True
            )
