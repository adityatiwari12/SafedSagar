import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import { AbsTab, DocumentsTab } from './ProductDetailPage'
import { getMessages, t as translate } from '../i18n/catalog'
import type { AbsAssessment, DocumentMeta } from '../api/productsApi'
import type { MessageKey } from '../i18n/types'

const en = getMessages('en')
const t = (key: MessageKey) => translate(en, key)

function freshAssessment(): AbsAssessment {
  return {
    id: null,
    product_id: 'p1',
    is_biological_resource: null,
    resource_description: null,
    origin: null,
    sourcing: null,
    involves_traditional_knowledge: null,
    purpose: null,
    user_entity_category: null,
    preliminary_framework: null,
    applicable_provisions: null,
    next_steps: null,
    status: 'not_started',
    updated_by_user_id: null,
    created_at: null,
    updated_at: null,
  }
}

test('ABS wizard steps forward and back without losing an earlier answer', async () => {
  const user = userEvent.setup()
  render(
    <AbsTab
      assessment={freshAssessment()}
      loading={false}
      error={null}
      saving={false}
      evidenceLoading={false}
      actionError={null}
      t={t}
      onRetry={vi.fn()}
      onSave={vi.fn()}
      onFindEvidence={vi.fn()}
    />,
  )

  expect(screen.getByText('Step 1 of 7')).toBeInTheDocument()
  expect(screen.getByText(t('abs.qIsBiologicalResource'))).toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: t('abs.yes') }))
  expect(screen.getByRole('button', { name: t('abs.yes') })).toHaveAttribute('aria-pressed', 'true')

  await user.click(screen.getByRole('button', { name: t('abs.next') }))
  expect(screen.getByText('Step 2 of 7')).toBeInTheDocument()
  expect(screen.getByText(t('abs.qResourceDescription'))).toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: t('abs.back') }))
  expect(screen.getByText('Step 1 of 7')).toBeInTheDocument()
  // The "Yes" answer from before stepping forward is still selected —
  // navigating the wizard must never silently drop an earlier step's answer.
  expect(screen.getByRole('button', { name: t('abs.yes') })).toHaveAttribute('aria-pressed', 'true')
})

test('ABS tab shows the saved summary (not the wizard) once an assessment has been saved, with an edit action back into the wizard', async () => {
  const user = userEvent.setup()
  const saved: AbsAssessment = {
    ...freshAssessment(),
    id: 'abs-1',
    is_biological_resource: true,
    status: 'in_progress',
    preliminary_framework: 'Structural placeholder framework text.',
    next_steps: ['Contact NBA for guidance.'],
  }

  render(
    <AbsTab
      assessment={saved}
      loading={false}
      error={null}
      saving={false}
      evidenceLoading={false}
      actionError={null}
      t={t}
      onRetry={vi.fn()}
      onSave={vi.fn()}
      onFindEvidence={vi.fn()}
    />,
  )

  expect(screen.getByText('Structural placeholder framework text.')).toBeInTheDocument()
  expect(screen.getByText('Contact NBA for guidance.')).toBeInTheDocument()
  expect(screen.queryByText('Step 1 of 7')).not.toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: t('abs.editCta') }))
  expect(screen.getByText('Step 1 of 7')).toBeInTheDocument()
})

test('Documents tab renders the loading state', () => {
  render(
    <DocumentsTab
      productId="p1"
      documents={null}
      loading={true}
      error={null}
      t={t}
      onRetry={vi.fn()}
      onUploaded={vi.fn()}
      onDeleted={vi.fn()}
    />,
  )
  expect(screen.getByText(t('documents.loading'))).toBeInTheDocument()
})

test('Documents tab renders the error state with a working retry', async () => {
  const user = userEvent.setup()
  const onRetry = vi.fn()
  render(
    <DocumentsTab
      productId="p1"
      documents={null}
      loading={false}
      error="Failed to load documents"
      t={t}
      onRetry={onRetry}
      onUploaded={vi.fn()}
      onDeleted={vi.fn()}
    />,
  )
  expect(screen.getByText('Failed to load documents')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: t('documents.retry') }))
  expect(onRetry).toHaveBeenCalledTimes(1)
})

test('Documents tab renders the empty state with an upload form visible (never a dead end)', () => {
  render(
    <DocumentsTab
      productId="p1"
      documents={[]}
      loading={false}
      error={null}
      t={t}
      onRetry={vi.fn()}
      onUploaded={vi.fn()}
      onDeleted={vi.fn()}
    />,
  )
  expect(screen.getByText(t('documents.emptyTitle'))).toBeInTheDocument()
  expect(screen.getByText(t('documents.uploadTitle'))).toBeInTheDocument()
  expect(screen.getByRole('button', { name: t('documents.uploadButton') })).toBeInTheDocument()
})

test('Documents tab renders a loaded document list with filename, size and actions', () => {
  const doc: DocumentMeta = {
    id: 'd1',
    owner_user_id: 'u1',
    organization_id: null,
    product_id: 'p1',
    case_id: null,
    filename: 'label.pdf',
    content_type: 'application/pdf',
    size_bytes: 2_400_000,
    doc_kind: 'label',
    status: 'active',
    uploaded_by_user_id: 'u1',
    created_at: '2026-09-01T00:00:00Z',
  }
  render(
    <DocumentsTab
      productId="p1"
      documents={[doc]}
      loading={false}
      error={null}
      t={t}
      onRetry={vi.fn()}
      onUploaded={vi.fn()}
      onDeleted={vi.fn()}
    />,
  )
  expect(screen.getByText('label.pdf')).toBeInTheDocument()
  expect(screen.getByText('2.3 MB')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: t('documents.download') })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: t('documents.delete') })).toBeInTheDocument()
})
