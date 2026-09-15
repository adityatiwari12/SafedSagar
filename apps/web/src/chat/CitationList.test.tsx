import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import { CitationList } from './CitationList'
import { ConfidenceBadge } from './ConfidenceBadge'

test('CitationList renders doc title and last verified date', () => {
  render(
    <CitationList
      citations={[
        {
          doc_id: 'ipindia-patents-act-1970',
          title: 'The Patents Act, 1970',
          section_or_article: 'Section 3(p)',
          last_verified_date: '2026-09-15',
        },
      ]}
    />,
  )
  expect(screen.getByText(/The Patents Act, 1970/)).toBeInTheDocument()
  expect(screen.getByText(/Last verified: 2026-09-15/)).toBeInTheDocument()
})

test('ConfidenceBadge shows abstention language for low band', () => {
  render(<ConfidenceBadge band="low" confidence={0.2} />)
  expect(screen.getByText(/Low confidence/i)).toBeInTheDocument()
  expect(screen.getByText(/human IP facilitator/i)).toBeInTheDocument()
})
