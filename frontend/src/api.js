/**
 * API client — upload + crosscheck (pattern from FullStack_RAG frontend/src/api.js).
 */

const API_BASE = ''

async function parseApiError(res, data) {
  const msg = data?.detail?.message || data?.detail || data?.message || res.statusText
  throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
}

export async function extractRfiPdf(file, { signal } = {}) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${API_BASE}/api/rfi/extract`, {
    method: 'POST',
    body: fd,
    signal,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) await parseApiError(res, data)
  return data
}

/** Upload multiple PDFs (multi-select or folder). Non-PDF files are skipped client-side. */
export async function extractRfiPdfBatch(files, { signal, failFast = false } = {}) {
  const pdfs = [...files].filter((f) => f.name?.toLowerCase().endsWith('.pdf'))
  if (!pdfs.length) throw new Error('No PDF files selected.')

  const fd = new FormData()
  for (const file of pdfs) {
    fd.append('files', file)
  }
  if (failFast) fd.append('fail_fast', 'true')

  const res = await fetch(`${API_BASE}/api/rfi/extract-batch`, {
    method: 'POST',
    body: fd,
    signal,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) await parseApiError(res, data)
  return data
}

export function pdfPreviewUrl(uploadId) {
  return `${API_BASE}/api/rfi/${encodeURIComponent(uploadId)}/file`
}

export function imageUrl(uploadId, imageFilename) {
  return `${API_BASE}/api/rfi/${encodeURIComponent(uploadId)}/images/${encodeURIComponent(imageFilename)}`
}

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`)
  return res.ok
}
