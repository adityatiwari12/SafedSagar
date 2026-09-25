import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { beforeEach, expect, test, vi } from 'vitest'
import { ChatAttachments } from './ChatAttachments'
import { productsApi } from '../api/productsApi'

vi.mock('../api/productsApi', () => ({
  productsApi: { uploadDocument: vi.fn(), downloadDocument: vi.fn() },
}))

beforeEach(() => {
  vi.clearAllMocks()
})

function pdfFile(name = 'evidence.pdf') {
  return new File(['%PDF-1.4 fake content'], name, { type: 'application/pdf' })
}

test('uploading a PDF calls the document endpoint with no product/case link, and shows the file', async () => {
  ;(productsApi.uploadDocument as ReturnType<typeof vi.fn>).mockResolvedValue({
    id: 'doc-1',
    owner_user_id: 'u1',
    organization_id: null,
    product_id: null,
    case_id: null,
    filename: 'evidence.pdf',
    content_type: 'application/pdf',
    size_bytes: 1234,
    doc_kind: 'other',
    status: 'active',
    uploaded_by_user_id: 'u1',
    created_at: new Date().toISOString(),
  })

  const { container } = render(createElement(ChatAttachments))

  const input = container.querySelector('#chat-attach-input') as HTMLInputElement
  fireEvent.change(input, { target: { files: [pdfFile()] } })

  await waitFor(() => expect(screen.getByText('evidence.pdf')).toBeInTheDocument())

  expect(productsApi.uploadDocument).toHaveBeenCalledWith({
    file: expect.any(File),
    docKind: 'other',
  })
})

test('rejects a non-PDF file without calling the upload endpoint', async () => {
  const { container } = render(createElement(ChatAttachments))

  const input = container.querySelector('#chat-attach-input') as HTMLInputElement
  const textFile = new File(['hello'], 'notes.txt', { type: 'text/plain' })
  fireEvent.change(input, { target: { files: [textFile] } })

  await waitFor(() => expect(screen.getByText(/Only PDF files/)).toBeInTheDocument())
  expect(productsApi.uploadDocument).not.toHaveBeenCalled()
})
