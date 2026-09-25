import { useRef, useState } from 'react'
import { ApiError } from '../api/http'
import { DocumentMeta, productsApi } from '../api/productsApi'

/** Lets the user attach a PDF to the chat session and see it really
 * uploaded/stored - NOT fed into retrieval, NOT linked to a product or
 * case, NOT part of the corpus the assistant answers from. Uses the same
 * POST /documents endpoint the Product Dossier's Documents tab uses, just
 * with no product_id/case_id, so it's a genuine stored file (survives
 * page reload server-side, downloadable, audit-logged) without touching
 * anything the LangGraph pipeline reads. */
export function ChatAttachments() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [items, setItems] = useState<DocumentMeta[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onFileChosen(file: File | undefined) {
    if (!file) return
    setError(null)
    if (file.type !== 'application/pdf') {
      setError('Only PDF files can be attached.')
      return
    }
    setUploading(true)
    try {
      const doc = await productsApi.uploadDocument({ file, docKind: 'other' })
      setItems((prev) => [doc, ...prev])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  async function download(doc: DocumentMeta) {
    try {
      const { blob, filename } = await productsApi.downloadDocument(doc.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename ?? doc.filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      setError('Failed to download attachment')
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="sr-only"
        id="chat-attach-input"
        onChange={(e) => void onFileChosen(e.target.files?.[0])}
      />
      <label
        htmlFor="chat-attach-input"
        className={`flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center border border-surface-border bg-white text-ink-faint hover:border-saffron hover:text-saffron-deep ${
          uploading ? 'pointer-events-none opacity-50' : ''
        }`}
        aria-label="Attach a PDF"
        title="Attach a PDF (stored, not used to answer questions)"
      >
        <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
          <path
            d="M17 8.5V16a4 4 0 0 1-8 0V7a2.5 2.5 0 0 1 5 0v8a1 1 0 0 1-2 0V8.5"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </label>

      {uploading && <span className="text-xs text-ink-faint">Uploading…</span>}
      {error && <span className="text-xs text-red-700">{error}</span>}

      {items.length > 0 && (
        <ul className="flex flex-wrap items-center gap-1.5">
          {items.map((doc) => (
            <li key={doc.id}>
              <button
                type="button"
                onClick={() => void download(doc)}
                className="flex items-center gap-1.5 border border-surface-border bg-ivory/60 px-2 py-1 text-xs text-ink hover:border-saffron"
                title="Attached — stored, not used to answer questions. Click to download."
              >
                <svg viewBox="0 0 24 24" fill="none" className="h-3 w-3 shrink-0 text-ink-faint" aria-hidden="true">
                  <path
                    d="M6 2h9l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinejoin="round"
                  />
                </svg>
                <span className="max-w-[10rem] truncate">{doc.filename}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
