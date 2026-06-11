"""Local disk storage for uploaded RFI PDFs and extracted assets."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
UPLOADS_DIR = DATA_ROOT / "uploads"


def new_upload_id() -> str:
    return str(uuid.uuid4())


def upload_dir(upload_id: str) -> Path:
    return UPLOADS_DIR / upload_id


def save_upload(
    upload_id: str,
    filename: str,
    pdf_bytes: bytes,
    metadata: dict,
) -> Path:
    d = upload_dir(upload_id)
    d.mkdir(parents=True, exist_ok=True)
    pdf_path = d / "source.pdf"
    pdf_path.write_bytes(pdf_bytes)
    meta = {
        "upload_id": upload_id,
        "filename": filename,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        **metadata,
    }
    (d / "metadata.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    return pdf_path


def load_metadata(upload_id: str) -> dict | None:
    path = upload_dir(upload_id) / "metadata.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def pdf_path(upload_id: str) -> Path:
    return upload_dir(upload_id) / "source.pdf"
