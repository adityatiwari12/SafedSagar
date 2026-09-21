import { Citation } from '../api/chatApi'
import { EvidenceList } from '../ui/primitives'

export function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null

  return (
    <EvidenceList
      items={citations.map((c) => ({
        title: c.title,
        docId: c.doc_id,
        provision: c.section_or_article ?? undefined,
        effectiveDate: c.last_verified_date ?? undefined,
        sourceUrl: c.source_url ?? undefined,
        why: 'Retrieved evidence supporting the answer — confirm against the official text.',
      }))}
    />
  )
}
