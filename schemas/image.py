"""Image extraction records."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ImageType = Literal["site_photo", "drawing", "logo", "stamp", "unknown", "skip"]


class ImageRecord(BaseModel):
    image_id: str
    inspection_id: str | None = None
    page_number: int
    source_ref: str
    image_path: str
    image_type: ImageType = "unknown"
    width: int = 0
    height: int = 0
    routing_confidence: float | None = None
    hash: str | None = None
    filter_reason: str | None = None
