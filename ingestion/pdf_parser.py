"""Extract RFI form fields and page text from inspection PDFs (PyMuPDF)."""
from __future__ import annotations

import re
from typing import Any

import fitz  # PyMuPDF

from schemas.inspection import InspectionOutcome, InspectionRecord, ParseStats, ParseStatus

_INSPECTION_ID = re.compile(
    r"(?:Inspection\s+No\.?\s*:?\s*)?([A-Z]?\d+/Inspection/[A-Z]+/\d+[A-Z]?)",
    re.I,
)
_LOCATION = re.compile(
    r"Location\s*:?\s*(.+?)(?=\n\s*Description of Works|\n\s*Subsequent Work|\Z)",
    re.I | re.S,
)
_DESC_WORKS = re.compile(
    r"Description of Works\s*(.+?)(?=\n\s*Subsequent Work|\n\s*Reference Drawing|\Z)",
    re.I | re.S,
)
_SUBSEQUENT = re.compile(
    r"Subsequent Work\s*(.+?)(?=\n\s*Reference Drawing|\n\s*No\. of Attached|\Z)",
    re.I | re.S,
)
_REF_DRAWINGS = re.compile(
    r"Reference Drawing No\.?\(s\)\s*(.+?)(?=\n\s*No\. of Attached|\n\s*We certify|\Z)",
    re.I | re.S,
)
_COMMENTS = re.compile(
    r"Comments:\s*(.+?)(?=\n\s*Inspected by:|\n\s*\* After immediate|\Z)",
    re.I | re.S,
)
_INSPECTED_BY = re.compile(
    r"Inspected by:\s*(.+?)(?=\n\s*Designation:|\n\s*Date:|\Z)",
    re.I | re.S,
)
_INSPECTION_DATE = re.compile(
    r"Date:\s*(\d{1,2}/\d{1,2}/\d{4})",
    re.I,
)


def _clean(value: str | None) -> str | None:
    if not value:
        return None
    text = re.sub(r"\s+", " ", value.replace("\r", "\n")).strip()
    return text or None


def _clean_comments(value: str | None) -> str | None:
    text = _clean(value)
    if not text:
        return None
    if text.lower().startswith("inspected by"):
        return None
    return text


def _outcome_section(text: str) -> str:
    m = re.search(
        r"The above inspection is:\s*(.+?)(?=Comments:|\* After immediate|\Z)",
        text,
        re.I | re.S,
    )
    return m.group(1) if m else text


def _detect_outcome(text: str) -> InspectionOutcome:
    section = _outcome_section(text)
    lower = section.lower()
    if re.search(r"(☑|☒|✓|\[x\])\s*rejected", lower):
        return "rejected"
    if re.search(r"(☑|☒|✓|\[x\])\s*conditionally accepted", lower):
        if "re-inspection is required" in lower:
            return "conditionally_accepted_reinspection"
        return "conditionally_accepted_no_reinspection"
    if re.search(r"(☑|☒|✓|\[x\])\s*accepted", lower):
        return "accepted"
    return "unknown"


def parse_pdf_pages(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Return per-page text (1-based page numbers)."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Cannot open PDF: {exc}") from exc
    pages: list[dict[str, Any]] = []
    try:
        for i, page in enumerate(doc, start=1):
            text = (page.get_text("text") or "").strip()
            pages.append({"page_number": i, "text": text})
    finally:
        doc.close()
    return pages


def build_parse_status(pages: list[dict[str, Any]]) -> ParseStatus:
    total = sum(len(p.get("text") or "") for p in pages)
    with_text = sum(1 for p in pages if (p.get("text") or "").strip())
    stats = ParseStats(
        page_count=len(pages),
        total_text_chars=total,
        pages_with_text=with_text,
    )
    if stats.page_count <= 0:
        return ParseStatus(
            ok=False,
            code="empty_document",
            message="PDF has no pages.",
            stats=stats,
        )
    if stats.total_text_chars <= 0:
        return ParseStatus(
            ok=False,
            code="no_extractable_text",
            message="No extractable text — PDF may be scanned/image-only.",
            hint="likely_image_only_or_scanned",
            stats=stats,
        )
    return ParseStatus(ok=True, code="ok", message="", stats=stats)


def extract_inspection_record(
    pages: list[dict[str, Any]],
    *,
    source_filename: str,
) -> InspectionRecord:
    full_text = "\n".join(p.get("text") or "" for p in pages)

    inspection_id = None
    m = _INSPECTION_ID.search(full_text)
    if m:
        inspection_id = m.group(1).strip()

    record = InspectionRecord(
        inspection_id=inspection_id,
        location=_clean(_LOCATION.search(full_text).group(1) if _LOCATION.search(full_text) else None),
        description_of_works=_clean(
            _DESC_WORKS.search(full_text).group(1) if _DESC_WORKS.search(full_text) else None
        ),
        subsequent_work=_clean(
            _SUBSEQUENT.search(full_text).group(1) if _SUBSEQUENT.search(full_text) else None
        ),
        inspection_outcome=_detect_outcome(full_text),
        inspector_comments=_clean_comments(
            _COMMENTS.search(full_text).group(1) if _COMMENTS.search(full_text) else None
        ),
        inspected_by=_clean(
            _INSPECTED_BY.search(full_text).group(1) if _INSPECTED_BY.search(full_text) else None
        ),
        inspection_date=_clean(
            _INSPECTION_DATE.search(full_text).group(1) if _INSPECTION_DATE.search(full_text) else None
        ),
        reference_drawing_nos=_clean(
            _REF_DRAWINGS.search(full_text).group(1) if _REF_DRAWINGS.search(full_text) else None
        ),
        source_document_refs=[source_filename],
    )
    return record


def parse_rfi_pdf(pdf_bytes: bytes, *, filename: str) -> tuple[InspectionRecord, ParseStatus, list[dict[str, Any]]]:
    pages = parse_pdf_pages(pdf_bytes)
    status = build_parse_status(pages)
    record = extract_inspection_record(pages, source_filename=filename)
    return record, status, pages
