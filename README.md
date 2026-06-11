# Construction Defect Vision

Train an image-only defect classifier from historical RFI PDFs. Phase 1 includes an **RFI upload crosscheck UI** to verify metadata and photo extraction.

See [initial_plan.md](initial_plan.md) and [docs/labeling_protocol.md](docs/labeling_protocol.md).

## Quick start — crosscheck UI

### One command (recommended)

```powershell
cd c:\Software\PythonProject\VLM
.\scripts\start-dev.ps1
```

Starts the backend in a new window and the frontend in the current terminal. Open http://localhost:5173.

**Single terminal** (Ctrl+C stops both):

```powershell
.\scripts\start-dev.ps1 -SingleWindow
```

**Stop servers:**

```powershell
.\scripts\stop-dev.ps1
```

### Manual start

**Backend (port 8000):**

```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend (port 5173):**

```powershell
cd frontend
npm install
npm run dev
```

### API

- `POST /api/rfi/extract` — multipart `file` (single .pdf)
- `POST /api/rfi/extract-batch` — multipart `files` (folder / multiple PDFs, max 100)
- `GET /api/rfi/{upload_id}/file` — inline PDF preview
- `GET /api/rfi/{upload_id}/images/{filename}` — extracted image
- `GET /health`

Uploads are stored under `data/uploads/` (gitignored).
