"""Pydantic models for inspection bundles and extraction crosscheck."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

InspectionOutcome = Literal[
    "accepted",
    "conditionally_accepted_no_reinspection",
    "conditionally_accepted_reinspection",
    "rejected",
    "unknown",
]


class FieldExtraction(BaseModel):
    """One metadata field and whether it was found in the PDF."""

    key: str
    label: str
    value: str | None = None
    found: bool = False
    required: bool = True


class InspectionRecord(BaseModel):
    inspection_id: str | None = None
    project_name: str | None = None
    document_type: str = "rfi"
    location: str | None = None
    description_of_works: str | None = None
    subsequent_work: str | None = None
    inspection_outcome: InspectionOutcome = "unknown"
    inspector_comments: str | None = None
    inspected_by: str | None = None
    inspection_date: str | None = None
    reference_drawing_nos: str | None = None
    source_document_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ParseStats(BaseModel):
    page_count: int = 0
    total_text_chars: int = 0
    pages_with_text: int = 0


class ParseStatus(BaseModel):
    ok: bool = True
    code: str = "ok"
    message: str = ""
    hint: str | None = None
    stats: ParseStats = Field(default_factory=ParseStats)


class ExtractionCrosscheck(BaseModel):
    """Summary for the upload UI: which fields we need vs extracted."""

    fields: list[FieldExtraction] = Field(default_factory=list)
    required_found: int = 0
    required_total: int = 0
    complete: bool = False

    @classmethod
    def from_inspection(cls, record: InspectionRecord) -> ExtractionCrosscheck:
        specs: list[tuple[str, str, str | None, bool]] = [
            ("inspection_id", "Inspection No.", record.inspection_id, True),
            ("location", "Location", record.location, True),
            ("description_of_works", "Description of Works", record.description_of_works, True),
            ("subsequent_work", "Subsequent Work", record.subsequent_work, True),
            ("inspection_outcome", "Inspection outcome", record.inspection_outcome, True),
            ("inspector_comments", "Inspector comments", record.inspector_comments, False),
            ("inspected_by", "Inspected by", record.inspected_by, False),
            ("inspection_date", "Inspection date", record.inspection_date, False),
            ("reference_drawing_nos", "Reference drawing(s)", record.reference_drawing_nos, False),
        ]
        fields = [
            FieldExtraction(
                key=key,
                label=label,
                value=value if value not in (None, "", "unknown") else None,
                found=bool(value and str(value).strip() and str(value) != "unknown"),
                required=required,
            )
            for key, label, value, required in specs
        ]
        required_fields = [f for f in fields if f.required]
        found = sum(1 for f in required_fields if f.found)
        total = len(required_fields)
        return cls(
            fields=fields,
            required_found=found,
            required_total=total,
            complete=found == total,
        )
