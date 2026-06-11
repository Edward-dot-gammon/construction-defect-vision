from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app

SAMPLE_PDF = Path(r"c:\Users\edwardlam\Downloads\J3968-Inspection-ARC-000002A_completed.pdf")

client = TestClient(app)


@pytest.mark.skipif(not SAMPLE_PDF.is_file(), reason="Sample PDF not on disk")
def test_rfi_extract_sample():
    with SAMPLE_PDF.open("rb") as f:
        res = client.post("/api/rfi/extract", files={"file": ("sample.pdf", f, "application/pdf")})
    assert res.status_code == 200
    data = res.json()
    assert data["inspection"]["inspection_id"] == "J3968/Inspection/ARC/000002A"
    assert data["inspection"]["inspection_outcome"] == "accepted"
    assert data["crosscheck"]["complete"] is True
    assert len(data["images"]) >= 1
    assert any(img["image_type"] == "site_photo" for img in data["images"])


@pytest.mark.skipif(not SAMPLE_PDF.is_file(), reason="Sample PDF not on disk")
def test_rfi_extract_batch():
    with SAMPLE_PDF.open("rb") as f:
        res = client.post(
            "/api/rfi/extract-batch",
            files=[("files", ("a.pdf", f.read(), "application/pdf")), ("files", ("b.pdf", f.read(), "application/pdf"))],
        )
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 2
    assert data["succeeded"] == 2
    assert data["failed"] == 0
    assert len(data["results"]) == 2
