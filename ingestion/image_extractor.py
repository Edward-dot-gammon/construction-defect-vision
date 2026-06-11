"""Extract embedded images from PDF pages and classify for training eligibility."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from schemas.image import ImageRecord, ImageType

MIN_IMAGE_PX = 80
LOGO_MAX_PX = 120
DRAWING_MIN_PX = 900


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _classify_image(
    width: int,
    height: int,
    page_width: float,
    page_height: float,
    *,
    page_text_chars: int = 0,
) -> tuple[ImageType, float, str | None]:
    """Heuristic routing: site photo vs drawing vs logo."""
    max_dim = max(width, height)
    min_dim = min(width, height)
    if max_dim < MIN_IMAGE_PX:
        return "logo", 0.9, "too_small"

    if max_dim <= LOGO_MAX_PX:
        return "logo", 0.85, "logo"

    # Attachment pages: little text, large embedded photo (common in RFI PDFs).
    if page_text_chars < 80 and max_dim >= 400:
        return "site_photo", 0.8, None

    page_cover = 0.0
    if page_width > 0 and page_height > 0:
        page_cover = (width * height) / (page_width * page_height)

    if max_dim >= DRAWING_MIN_PX and page_cover > 0.55 and page_text_chars > 200:
        return "drawing", 0.75, "drawing"

    if min_dim < 200 and page_cover < 0.15:
        return "stamp", 0.7, "stamp"

    return "site_photo", 0.6, None


def extract_images_from_pdf(
    pdf_bytes: bytes,
    *,
    output_dir: Path,
    inspection_id: str | None,
    prefix: str = "img",
) -> list[ImageRecord]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[ImageRecord] = []
    seen_hashes: set[str] = set()

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        for page_index, page in enumerate(doc, start=1):
            page_rect = page.rect
            page_text_chars = len((page.get_text("text") or "").strip())
            for img_index, img in enumerate(page.get_images(full=True), start=1):
                xref = img[0]
                try:
                    extracted = doc.extract_image(xref)
                except Exception:
                    continue
                data = extracted.get("image") or b""
                if not data:
                    continue
                digest = _sha256(data)
                if digest in seen_hashes:
                    continue
                seen_hashes.add(digest)

                width = int(extracted.get("width") or 0)
                height = int(extracted.get("height") or 0)
                ext = extracted.get("ext") or "png"
                image_type, confidence, filter_reason = _classify_image(
                    width,
                    height,
                    float(page_rect.width),
                    float(page_rect.height),
                    page_text_chars=page_text_chars,
                )
                image_id = f"{prefix}_p{page_index}_{img_index}"
                filename = f"{image_id}.{ext}"
                path = output_dir / filename
                path.write_bytes(data)

                records.append(
                    ImageRecord(
                        image_id=image_id,
                        inspection_id=inspection_id,
                        page_number=page_index,
                        source_ref=f"page:{page_index}/xref:{xref}",
                        image_path=str(path),
                        image_type=image_type,
                        width=width,
                        height=height,
                        routing_confidence=confidence,
                        hash=digest,
                        filter_reason=filter_reason,
                    )
                )
    finally:
        doc.close()

    return records
