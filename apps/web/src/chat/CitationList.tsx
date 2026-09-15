import { Citation } from '../api/chatApi'

export function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null

  return (
    <section className="gov-panel mt-4 p-4" aria-labelledby="citations-heading">
      <h3 id="citations-heading" className="text-base font-bold text-navy">
        Sources cited
      </h3>
      <ol className="mt-3 space-y-3">
        {citations.map((c, i) => (
          <li key={`${c.doc_id}-${i}`} className="border-l-4 border-primary pl-3 text-sm">
            <p className="font-semibold text-ink">
              [{i + 1}] {c.title}
            </p>
            <p className="text-ink-muted">
              <span className="font-medium">{c.doc_id}</span>
              {c.section_or_article ? ` · ${c.section_or_article}` : ''}
            </p>
            <p className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-ink-faint">
              {c.last_verified_date && <span>Last verified: {c.last_verified_date}</span>}
              {c.source_url && (
                <a
                  href={c.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary underline hover:text-primary-dark"
                >
                  Open source
                </a>
              )}
            </p>
          </li>
        ))}
      </ol>
    </section>
  )
}
