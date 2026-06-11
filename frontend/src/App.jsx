import { useCallback, useEffect, useRef, useState } from 'react'
import { checkHealth, extractRfiPdf, extractRfiPdfBatch, imageUrl, pdfPreviewUrl } from './api.js'

const OUTCOME_LABELS = {
  accepted: 'Accepted',
  conditionally_accepted_no_reinspection: 'Conditionally accepted (no re-inspection)',
  conditionally_accepted_reinspection: 'Conditionally accepted (re-inspection required)',
  rejected: 'Rejected',
  unknown: 'Unknown',
}

function FieldRow({ field }) {
  return (
    <tr className={field.found ? 'row-ok' : field.required ? 'row-miss' : 'row-optional'}>
      <td className="field-label">
        {field.label}
        {field.required && <span className="req">*</span>}
      </td>
      <td className="field-status">{field.found ? '✓' : field.required ? '✗' : '—'}</td>
      <td className="field-value">{field.value || <em className="muted">Not extracted</em>}</td>
    </tr>
  )
}

function ImageCard({ uploadId, image }) {
  const name = image.image_path.split(/[/\\]/).pop()
  const src = imageUrl(uploadId, name)
  const trainable = image.image_type === 'site_photo' && !image.filter_reason
  return (
    <div className={`image-card type-${image.image_type}`}>
      <img src={src} alt={image.image_id} loading="lazy" />
      <div className="image-meta">
        <strong>{image.image_id}</strong>
        <span>p.{image.page_number} · {image.width}×{image.height}</span>
        <span className="badge">{image.image_type}</span>
        {image.filter_reason && <span className="badge warn">{image.filter_reason}</span>}
        {trainable && <span className="badge ok">training candidate</span>}
      </div>
    </div>
  )
}

function ExtractionDetail({ result, showPages, onTogglePages }) {
  const sitePhotos = result?.images?.filter((i) => i.image_type === 'site_photo') || []
  const filtered = result?.images?.filter((i) => i.image_type !== 'site_photo') || []

  return (
    <div className="layout">
      <section className="panel">
        <h2>
          Metadata crosscheck{' '}
          <span className={result.crosscheck.complete ? 'pill ok' : 'pill warn'}>
            {result.crosscheck.required_found}/{result.crosscheck.required_total} required
          </span>
        </h2>
        <table className="fields-table">
          <thead>
            <tr>
              <th>Field</th>
              <th></th>
              <th>Extracted value</th>
            </tr>
          </thead>
          <tbody>
            {result.crosscheck.fields.map((f) => (
              <FieldRow key={f.key} field={f} />
            ))}
          </tbody>
        </table>
        <p className="outcome">
          Outcome:{' '}
          <strong>
            {OUTCOME_LABELS[result.inspection.inspection_outcome] || result.inspection.inspection_outcome}
          </strong>
        </p>
        {result.parse_status && !result.parse_status.ok && (
          <p className="parse-hint">{result.parse_status.message}</p>
        )}
      </section>

      <section className="panel pdf-panel">
        <h2>PDF preview</h2>
        <iframe title="PDF preview" src={pdfPreviewUrl(result.upload_id)} className="pdf-frame" />
      </section>

      <section className="panel full">
        <h2>
          Extracted images ({result.images.length}) — site photos: {sitePhotos.length}
        </h2>
        {result.images.length === 0 ? (
          <p className="muted">No embedded images found in this PDF.</p>
        ) : (
          <>
            {sitePhotos.length > 0 && (
              <>
                <h3>Site photos</h3>
                <div className="image-grid">
                  {sitePhotos.map((img) => (
                    <ImageCard key={img.image_id} uploadId={result.upload_id} image={img} />
                  ))}
                </div>
              </>
            )}
            {filtered.length > 0 && (
              <>
                <h3>Filtered (drawings / logos / other)</h3>
                <div className="image-grid">
                  {filtered.map((img) => (
                    <ImageCard key={img.image_id} uploadId={result.upload_id} image={img} />
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </section>

      <section className="panel full">
        <button type="button" className="link-btn" onClick={onTogglePages}>
          {showPages ? 'Hide' : 'Show'} per-page text ({result.page_previews.length} pages)
        </button>
        {showPages && (
          <div className="page-text">
            {result.page_previews.map((p) => (
              <details key={p.page_number} open={p.page_number <= 2}>
                <summary>
                  Page {p.page_number} ({p.char_count} chars)
                </summary>
                <pre>{p.text || '(empty)'}</pre>
              </details>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

export default function App() {
  const fileInputRef = useRef(null)
  const folderInputRef = useRef(null)
  const abortRef = useRef(null)
  const [backendOk, setBackendOk] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [batch, setBatch] = useState(null)
  const [selectedUploadId, setSelectedUploadId] = useState(null)
  const [showPages, setShowPages] = useState(false)

  useEffect(() => {
    checkHealth().then(setBackendOk).catch(() => setBackendOk(false))
  }, [])

  const runExtract = useCallback(async (fn) => {
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac
    setRunning(true)
    setError('')
    setResult(null)
    setBatch(null)
    setSelectedUploadId(null)
    setShowPages(false)
    try {
      await fn(ac.signal)
    } catch (err) {
      if (err.name === 'AbortError') return
      setError(err.message || 'Upload failed')
    } finally {
      setRunning(false)
    }
  }, [])

  const onPickFile = useCallback(
    async (e) => {
      const file = e.target.files?.[0]
      e.target.value = ''
      if (!file) return
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setError('Please select a .pdf file.')
        return
      }
      await runExtract(async (signal) => {
        const data = await extractRfiPdf(file, { signal })
        setResult(data)
      })
    },
    [runExtract],
  )

  const onPickFolder = useCallback(
    async (e) => {
      const fileList = e.target.files
      e.target.value = ''
      if (!fileList?.length) return
      await runExtract(async (signal) => {
        const data = await extractRfiPdfBatch(fileList, { signal })
        setBatch(data)
        if (data.results?.length) {
          setSelectedUploadId(data.results[0].upload_id)
        }
      })
    },
    [runExtract],
  )

  const selectedResult =
    batch?.results?.find((r) => r.upload_id === selectedUploadId) ||
    (batch?.results?.length === 1 ? batch.results[0] : null)

  const activeResult = result || selectedResult

  return (
    <div className="app">
      <header>
        <h1>RFI Extraction Crosscheck</h1>
        <p className="subtitle">
          Upload completed inspection PDFs to verify metadata and photo extraction (Phase 1).
        </p>
        <div className="health">
          Backend:{' '}
          {backendOk === null ? '…' : backendOk ? (
            <span className="ok">connected</span>
          ) : (
            <span className="err">offline — run scripts\start-dev.ps1</span>
          )}
        </div>
      </header>

      <section className="upload-bar">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          style={{ display: 'none' }}
          onChange={onPickFile}
        />
        <input
          ref={folderInputRef}
          type="file"
          accept=".pdf,application/pdf"
          multiple
          webkitdirectory=""
          directory=""
          style={{ display: 'none' }}
          onChange={onPickFolder}
        />
        <button type="button" disabled={running} onClick={() => fileInputRef.current?.click()}>
          {running ? 'Extracting…' : 'Upload PDF'}
        </button>
        <button type="button" disabled={running} onClick={() => folderInputRef.current?.click()}>
          Upload folder
        </button>
        {result && (
          <span className="file-meta">
            {result.filename} · {result.duration_ms}ms
          </span>
        )}
        {batch && (
          <span className="file-meta">
            {batch.succeeded}/{batch.count} OK · {batch.complete_count} complete · {batch.duration_ms}ms
          </span>
        )}
      </section>

      {error && <div className="banner err">{error}</div>}
      {result?.warnings?.map((w) => (
        <div key={w} className="banner warn">
          {w}
        </div>
      ))}

      {batch && (
        <section className="panel full batch-panel">
          <h2>
            Batch results{' '}
            <span className={batch.ok ? 'pill ok' : 'pill warn'}>
              {batch.succeeded} succeeded, {batch.failed} failed
            </span>
          </h2>
          {batch.errors?.length > 0 && (
            <div className="batch-errors">
              {batch.errors.map((e) => (
                <div key={e.filename} className="banner err compact">
                  <strong>{e.filename}</strong>: {e.message}
                </div>
              ))}
            </div>
          )}
          <table className="batch-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Inspection ID</th>
                <th>Outcome</th>
                <th>Fields</th>
                <th>Photos</th>
                <th>Warnings</th>
              </tr>
            </thead>
            <tbody>
              {batch.results.map((row) => {
                const photos = row.images.filter((i) => i.image_type === 'site_photo').length
                const selected = row.upload_id === selectedUploadId
                return (
                  <tr
                    key={row.upload_id}
                    className={`batch-row ${selected ? 'selected' : ''} ${row.crosscheck.complete ? '' : 'incomplete'}`}
                    onClick={() => {
                      setSelectedUploadId(row.upload_id)
                      setShowPages(false)
                    }}
                  >
                    <td>{row.filename}</td>
                    <td>{row.inspection.inspection_id || '—'}</td>
                    <td>{OUTCOME_LABELS[row.inspection.inspection_outcome] || row.inspection.inspection_outcome}</td>
                    <td>
                      {row.crosscheck.required_found}/{row.crosscheck.required_total}
                    </td>
                    <td>{photos}</td>
                    <td>{row.warnings?.length || 0}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <p className="muted batch-hint">Click a row to inspect metadata, PDF preview, and images below.</p>
        </section>
      )}

      {activeResult && (
        <>
          {batch && activeResult.warnings?.map((w) => (
            <div key={`${activeResult.upload_id}-${w}`} className="banner warn">
              <strong>{activeResult.filename}:</strong> {w}
            </div>
          ))}
          <ExtractionDetail
            result={activeResult}
            showPages={showPages}
            onTogglePages={() => setShowPages((v) => !v)}
          />
        </>
      )}
    </div>
  )
}
