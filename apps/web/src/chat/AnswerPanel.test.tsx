import { render, screen } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { expect, test } from 'vitest'
import { AnswerPanel } from './AnswerPanel'
import { ChatTurnResponse, RelatedProvision } from '../api/chatApi'
import { LanguageProvider } from '../i18n/LanguageContext'

function wrapper(props: { children: ReactNode }) {
  return createElement(LanguageProvider, null, props.children)
}

function renderPanel(response: ChatTurnResponse) {
  return render(createElement(AnswerPanel, { response }), { wrapper })
}

const BASE_RESPONSE: ChatTurnResponse = {
  conversationId: 'conv-1',
  classification: { product_type: 'classical_or_generic_medicine', ip_type: 'patent' },
  jurisdiction: 'india',
  answer: 'This is the assistant answer text.',
  citations: [],
  confidence: 0.8,
  confidence_band: 'high',
  escalate_recommended: false,
}

function relatedProvision(overrides: Partial<RelatedProvision> = {}): RelatedProvision {
  return {
    doc_id: 'ipindia-patents-act-1970',
    title: 'The Patents Act, 1970',
    section_or_article: '3',
    jurisdiction: 'india',
    relation: 'RELATES_TO',
    via: 'Traditional knowledge --RELATES_TO--> The Patents Act, 1970 - Section 3 [curated; source: ipindia-patents-act-1970 3]',
    source_url: 'https://ipindia.gov.in/patents-act.pdf',
    ...overrides,
  }
}

test('does not render a related provisions section when the array is empty or absent', () => {
  renderPanel({ ...BASE_RESPONSE, related_provisions: [] })
  expect(screen.queryByText('Related provisions')).not.toBeInTheDocument()

  renderPanel(BASE_RESPONSE)
  expect(screen.queryAllByText('Related provisions')).toHaveLength(0)
})

test('renders related provisions with title, jurisdiction, plain-language via text, and source link', () => {
  renderPanel({
    ...BASE_RESPONSE,
    related_provisions: [relatedProvision()],
  })

  expect(screen.getByText('Related provisions')).toBeInTheDocument()
  expect(screen.getAllByText(/The Patents Act, 1970/).length).toBeGreaterThan(0)
  // "India" also appears in the Assessment cluster's jurisdiction field, so
  // there are two on the page - assert on the related-provisions badge only.
  expect(screen.getAllByText('India').length).toBeGreaterThanOrEqual(2)
  // The raw --RELATES_TO--> marker and bracketed provenance are reformatted
  // away, but the human-readable path survives.
  expect(
    screen.getByText(/Connected through: Traditional knowledge → The Patents Act, 1970 - Section 3/),
  ).toBeInTheDocument()
  expect(screen.queryByText(/--RELATES_TO-->/)).not.toBeInTheDocument()
  expect(screen.queryByText(/\[curated/)).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'View source' })).toHaveAttribute(
    'href',
    'https://ipindia.gov.in/patents-act.pdf',
  )
})

test('caps related provisions at 5 visible with a "+N more" affordance', () => {
  const items = Array.from({ length: 7 }, (_, i) =>
    relatedProvision({ doc_id: `doc-${i}`, title: `Statute ${i}`, section_or_article: String(i) }),
  )
  renderPanel({ ...BASE_RESPONSE, related_provisions: items })

  for (let i = 0; i < 5; i += 1) {
    expect(screen.getByText(`Statute ${i}`)).toBeInTheDocument()
  }
  expect(screen.queryByText('Statute 5')).not.toBeInTheDocument()
  expect(screen.getByText('+2 more')).toBeInTheDocument()
})

test('shows the "considered earlier context" note only when used_conversation_context is true', () => {
  renderPanel({ ...BASE_RESPONSE, used_conversation_context: true })
  expect(screen.getByText('Building on earlier in this conversation.')).toBeInTheDocument()
})

test('does not show the earlier-context note on the first turn or when false', () => {
  renderPanel(BASE_RESPONSE)
  expect(screen.queryByText('Building on earlier in this conversation.')).not.toBeInTheDocument()

  renderPanel({ ...BASE_RESPONSE, used_conversation_context: false })
  expect(screen.queryByText('Building on earlier in this conversation.')).not.toBeInTheDocument()
})

test('renders an "answered by" line when answered_by is present', () => {
  renderPanel({
    ...BASE_RESPONSE,
    answered_by: { provider: 'ollama', model: 'llama3.2', fallback_used: false },
  })
  expect(screen.getByText(/Answered by ollama · llama3.2/)).toBeInTheDocument()
  expect(screen.queryByText(/fallback model/)).not.toBeInTheDocument()
})

test('plainly states when the local fallback model was used', () => {
  renderPanel({
    ...BASE_RESPONSE,
    answered_by: { provider: 'groq', model: 'llama-3.1-70b', fallback_used: true },
  })
  expect(screen.getByText(/Answered by groq · llama-3.1-70b/)).toBeInTheDocument()
  expect(
    screen.getByText(/local fallback model/),
  ).toBeInTheDocument()
})

test('does not render an "answered by" line when answered_by is null or absent', () => {
  renderPanel({ ...BASE_RESPONSE, answered_by: null })
  expect(screen.queryByText(/Answered by/)).not.toBeInTheDocument()

  renderPanel(BASE_RESPONSE)
  expect(screen.queryAllByText(/Answered by/)).toHaveLength(0)
})
