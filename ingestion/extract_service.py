"""Shared RFI PDF extraction logic for single and batch upload."""
from __future__ import annotations

import time
from pathlib import Path

from ingestion.image_extractor import extract_images_from_pdf
from ingestion.pdf_parser import parse_rfi_pdf
from ingestion.storage import save_upload, upload_dir, new_upload_id
from schemas.api import PageTextPreview, RfiExtractionResponse
from schemas.inspection import ExtractionCrosscheck

_MAX_PDF = 40 * 1024 * 1024


def process_rfi_pdf_bytes(raw: bytes, *, filename: str) -> RfiExtractionResponse:
    if len(raw) > _MAX_PDF:
        raise ValueError(f"PDF too large (max {_MAX_PDF // (1024 * 1024)} MiB): {filename}")
    if not raw:
        raise ValueError(f"Empty file: {filename}")

    t0 = time.perf_counter()
    upload_id = new_upload_id()

    record, parse_status, pages = parse_rfi_pdf(raw, filename=filename)

    warnings: list[str] = []
    if not parse_status.ok:
        warnings.append(parse_status.message)

    images_dir = upload_dir(upload_id) / "images"
    images = extract_images_from_pdf(
        raw,
        output_dir=images_dir,
        inspection_id=record.inspection_id,
        prefix="att",
    )
    site_photos = [img for img in images if img.image_type == "site_photo"]
    if not site_photos:
        warnings.append("No site photos detected — check attachments or image extraction.")

    crosscheck = ExtractionCrosscheck.from_inspection(record)
    if not crosscheck.complete:
        warnings.append(
            f"Missing {crosscheck.required_total - crosscheck.required_found} required metadata field(s)."
        )

    page_previews = [
        PageTextPreview(
            page_number=int(p["page_number"]),
            text=(p.get("text") or "")[:4000],
            char_count=len(p.get("text") or ""),
        )
        for p in pages
    ]

    save_upload(
        upload_id,
        filename,
        raw,
        metadata={
            "inspection_id": record.inspection_id,
            "crosscheck_complete": crosscheck.complete,
            "image_count": len(images),
            "site_photo_count": len(site_photos),
        },
    )

    duration_ms = (time.perf_counter() - t0) * 1000
    return RfiExtractionResponse(
        upload_id=upload_id,
        filename=filename,
        inspection=record,
        crosscheck=crosscheck,
        parse_status=parse_status,
        images=images,
        page_previews=page_previews,
        pdf_url=f"/api/rfi/{upload_id}/file",
        warnings=warnings,
        duration_ms=round(duration_ms, 1),
    )
