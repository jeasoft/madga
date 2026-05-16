"""Image optimization: resize-on-upload + WebP variants.

Wired via a ``post_save`` signal on ``MediaFile`` in ``madga.signals``.
For each uploaded image, generates ``sm/md/lg/xl`` WebP variants next
to the original and stores their URLs in ``MediaFile.variants``.
Public templates can then use ``{{ media.srcset }}`` to emit a
responsive image without any extra work from the host project.

Failures are intentionally silent — a missing Pillow plugin or a
corrupt upload should never block a successful save.
"""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from madga.models import MediaFile


logger = logging.getLogger(__name__)


# (suffix, max_width, quality)
VARIANT_SIZES = [
    ("sm", 480, 78),
    ("md", 960, 80),
    ("lg", 1440, 82),
    ("xl", 1920, 82),
]


def optimize(media: "MediaFile") -> bool:
    """Generate WebP variants for an image MediaFile.

    Returns True on success, False if the file is not an image or if
    something went wrong (errors are logged, never raised).
    """
    if media.file_type != "image" or not media.file:
        return False

    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow not installed; skipping image optimization")
        return False

    try:
        media.file.open("rb")
        try:
            img = Image.open(media.file)
            img.load()
        finally:
            media.file.close()
    except Exception as e:  # noqa: BLE001
        logger.warning("imageopt: failed to open %s: %s", media.file.name, e)
        return False

    # Backfill width/height while we're here
    media.width, media.height = img.size

    # Normalize mode for WebP (handles palette + alpha)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.mode else "RGB")

    base = Path(media.file.name)
    stem = base.stem
    folder = str(base.parent)
    storage = media.file.storage

    variants = {}
    for suffix, max_w, quality in VARIANT_SIZES:
        # Don't upscale: skip a variant bigger than the source
        if media.width and max_w > media.width and suffix != "xl":
            continue

        w = min(max_w, media.width or max_w)
        h = int(round((w / (media.width or w)) * (media.height or 1)))

        resized = img.copy()
        resized.thumbnail((w, h), Image.LANCZOS)

        buf = io.BytesIO()
        save_kwargs = {"quality": quality, "method": 4}
        try:
            resized.save(buf, format="WEBP", **save_kwargs)
        except Exception as e:  # noqa: BLE001
            logger.warning("imageopt: WEBP save failed for %s/%s: %s", media.id, suffix, e)
            continue
        buf.seek(0)

        out_name = f"{folder}/{stem}.{suffix}.webp" if folder and folder != "." else f"{stem}.{suffix}.webp"
        try:
            saved_name = storage.save(out_name, buf)
            url = storage.url(saved_name)
        except Exception as e:  # noqa: BLE001
            logger.warning("imageopt: storage save failed for %s: %s", out_name, e)
            continue

        variants[suffix] = {
            "url": url,
            "width": resized.size[0],
            "height": resized.size[1],
            "format": "webp",
        }

    if not variants:
        return False

    # Save variants without re-triggering the post_save signal infinite loop.
    type(media).objects.filter(pk=media.pk).update(
        variants=variants,
        width=media.width,
        height=media.height,
    )
    return True
