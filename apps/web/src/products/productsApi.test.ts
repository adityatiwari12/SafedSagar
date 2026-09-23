import { beforeEach, afterEach, expect, test, vi } from 'vitest'
import { productsApi, summarizeCompliance, type ComplianceItem } from '../api/productsApi'
import { ApiError } from '../api/http'

const NOW = '2026-09-18T00:00:00Z'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
  localStorage.clear()
})
afterEach(() => {
  vi.unstubAllGlobals()
})

test('create posts to /products with the given body', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 201,
    json: async () => ({
      id: 'p1',
      owner_user_id: 'u1',
      name: 'Ashwagandha capsules',
      created_at: NOW,
      updated_at: NOW,
    }),
  })

  const product = await productsApi.create({ name: 'Ashwagandha capsules' })

  expect(product.id).toBe('p1')
  const [url, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/products')
  expect(init.method).toBe('POST')
  expect(JSON.parse(init.body)).toEqual({ name: 'Ashwagandha capsules' })
})

test('list returns the parsed products array', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => [
      { id: 'p1', owner_user_id: 'u1', name: 'Product A', created_at: NOW, updated_at: NOW },
      { id: 'p2', owner_user_id: 'u1', name: 'Product B', created_at: NOW, updated_at: NOW },
    ],
  })

  const products = await productsApi.list()

  expect(products).toHaveLength(2)
  expect(products[0].name).toBe('Product A')
  const [url] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/products')
})

test('get surfaces a non-ok response as ApiError', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: false,
    status: 404,
    statusText: 'Not Found',
    json: async () => ({ detail: 'Product not found' }),
  })

  await expect(productsApi.get('missing')).rejects.toBeInstanceOf(ApiError)
  await expect(productsApi.get('missing')).rejects.toMatchObject({ status: 404 })
})

test('getCases hits /products/{id}/cases and parses the extended case list', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => [
      {
        id: 'c1',
        status: 'open',
        queue: 'ip',
        risk_level: 'high',
        question: 'Can I patent this?',
        answer: '',
        reason: null,
        product_classification: null,
        jurisdiction: 'india',
        confidence_score: 0.4,
        confidence_level: 'low',
        assigned_facilitator_email: null,
        user_email: 'a@b.com',
        created_at: NOW,
        closed_at: null,
        resolution_summary: null,
        product_id: 'p1',
        product_name: 'Ashwagandha capsules',
      },
    ],
  })

  const cases = await productsApi.getCases('p1')

  expect(cases).toHaveLength(1)
  expect(cases[0]).toMatchObject({ id: 'c1', product_id: 'p1', product_name: 'Ashwagandha capsules' })
  const [url] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/products/p1/cases')
})

const COMPLIANCE_RESPONSE = {
  items: [
    {
      id: 'ci1',
      product_id: 'p1',
      area: 'classification',
      status: 'unknown',
      applicability_reason: 'Applies to every product.',
      notes: null,
      evidence: null,
      updated_by_user_id: null,
      created_at: NOW,
      updated_at: NOW,
    },
  ],
  summary: {
    unknown: 1,
    action_required: 0,
    under_review: 0,
    complete: 0,
    not_applicable: 0,
    total: 1,
  },
}

test('getCompliance GETs /products/{id}/compliance', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => COMPLIANCE_RESPONSE,
  })

  const checklist = await productsApi.getCompliance('p1')

  expect(checklist.items).toHaveLength(1)
  expect(checklist.summary.total).toBe(1)
  const [url, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/products/p1/compliance')
  expect(init.method ?? 'GET').toBe('GET')
})

test('generateCompliance POSTs with the with_evidence query flag', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => COMPLIANCE_RESPONSE,
  })

  await productsApi.generateCompliance('p1', true)

  const [url, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/products/p1/compliance?with_evidence=true')
  expect(init.method).toBe('POST')
})

test('generateCompliance defaults with_evidence to false', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => COMPLIANCE_RESPONSE,
  })

  await productsApi.generateCompliance('p1')

  const [url] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('with_evidence=false')
})

test('updateComplianceItem PATCHes /products/{id}/compliance/{itemId} with the given body', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ ...COMPLIANCE_RESPONSE.items[0], status: 'complete' }),
  })

  const item = await productsApi.updateComplianceItem('p1', 'ci1', { status: 'complete' })

  expect(item.status).toBe('complete')
  const [url, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/products/p1/compliance/ci1')
  expect(init.method).toBe('PATCH')
  expect(JSON.parse(init.body)).toEqual({ status: 'complete' })
})

test('updateComplianceItem surfaces a 403 as ApiError', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: false,
    status: 403,
    statusText: 'Forbidden',
    json: async () => ({ detail: 'Not your product' }),
  })

  await expect(
    productsApi.updateComplianceItem('p1', 'ci1', { status: 'complete' }),
  ).rejects.toMatchObject({ status: 403 })
})

test('summarizeCompliance tallies items by status into the summary shape the checklist API returns', () => {
  const items: ComplianceItem[] = [
    { ...COMPLIANCE_RESPONSE.items[0], id: 'a', status: 'complete' },
    { ...COMPLIANCE_RESPONSE.items[0], id: 'b', status: 'complete' },
    { ...COMPLIANCE_RESPONSE.items[0], id: 'c', status: 'action_required' },
    { ...COMPLIANCE_RESPONSE.items[0], id: 'd', status: 'unknown' },
  ] as ComplianceItem[]

  const summary = summarizeCompliance(items)

  expect(summary).toEqual({
    unknown: 1,
    action_required: 1,
    under_review: 0,
    complete: 2,
    not_applicable: 0,
    total: 4,
  })
})

const ABS_RESPONSE = {
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

test('getAbsAssessment GETs /products/{id}/abs', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ABS_RESPONSE,
  })

  const assessment = await productsApi.getAbsAssessment('p1')

  expect(assessment.status).toBe('not_started')
  const [url, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/products/p1/abs')
  expect(init.method ?? 'GET').toBe('GET')
})

test('saveAbsAssessment PUTs the full answer set and appends with_evidence correctly', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ ...ABS_RESPONSE, id: 'abs-1', status: 'in_progress' }),
  })

  await productsApi.saveAbsAssessment('p1', { is_biological_resource: true, origin: 'india' }, true)

  const [url, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/products/p1/abs?with_evidence=true')
  expect(init.method).toBe('PUT')
  expect(JSON.parse(init.body)).toEqual({ is_biological_resource: true, origin: 'india' })
})

test('saveAbsAssessment defaults with_evidence to false', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ABS_RESPONSE,
  })

  await productsApi.saveAbsAssessment('p1', {})

  const [url] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('with_evidence=false')
})

test('listDocuments GETs /documents with the product_id query param', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => [],
  })

  await productsApi.listDocuments('p1')

  const [url] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/documents?product_id=p1')
})

test('removeDocument DELETEs /documents/{id}', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, status: 204 })

  await productsApi.removeDocument('d1')

  const [url, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/documents/d1')
  expect(init.method).toBe('DELETE')
})

test('downloadDocument fetches the binary with the auth header and parses the filename from Content-Disposition', async () => {
  const blob = new Blob(['pdf-bytes'])
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    headers: { get: (name: string) => (name === 'Content-Disposition' ? 'attachment; filename="label.pdf"' : null) },
    blob: async () => blob,
  })

  const result = await productsApi.downloadDocument('d1')

  expect(result.filename).toBe('label.pdf')
  expect(result.blob).toBe(blob)
  const [url] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/documents/d1/download')
})

test('downloadDocument surfaces a non-ok response as ApiError using the server detail', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: false,
    status: 403,
    statusText: 'Forbidden',
    json: async () => ({ detail: 'Not your document' }),
  })

  await expect(productsApi.downloadDocument('d1')).rejects.toMatchObject({
    status: 403,
    message: 'Not your document',
  })
})

test('downloadReport GETs /products/{id}/report and returns the PDF blob', async () => {
  const blob = new Blob(['%PDF-1.4'])
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    headers: {
      get: (name: string) =>
        name === 'Content-Disposition' ? 'attachment; filename="Ashwagandha-assessment-report.pdf"' : null,
    },
    blob: async () => blob,
  })

  const result = await productsApi.downloadReport('p1')

  expect(result.filename).toBe('Ashwagandha-assessment-report.pdf')
  const [url] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/products/p1/report')
})

class MockXHR {
  static instances: MockXHR[] = []
  method = ''
  url = ''
  status = 0
  statusText = ''
  responseText = ''
  upload: { onprogress: ((e: { lengthComputable: boolean; loaded: number; total: number }) => void) | null } = {
    onprogress: null,
  }
  onload: (() => void) | null = null
  onerror: (() => void) | null = null
  requestHeaders: Record<string, string> = {}
  sentBody: FormData | null = null

  open(method: string, url: string) {
    this.method = method
    this.url = url
  }
  setRequestHeader(name: string, value: string) {
    this.requestHeaders[name] = value
  }
  send(body: FormData) {
    this.sentBody = body
    MockXHR.instances.push(this)
  }
}

test('uploadDocument POSTs multipart form data with the file, doc_kind and product_id fields', async () => {
  MockXHR.instances = []
  vi.stubGlobal('XMLHttpRequest', MockXHR as unknown as typeof XMLHttpRequest)

  const file = new File(['hello'], 'label.pdf', { type: 'application/pdf' })
  const promise = productsApi.uploadDocument({ file, docKind: 'label', productId: 'p1' })

  const xhr = MockXHR.instances[0]
  expect(xhr.method).toBe('POST')
  expect(xhr.url).toContain('/documents')
  expect(xhr.sentBody?.get('doc_kind')).toBe('label')
  expect(xhr.sentBody?.get('product_id')).toBe('p1')
  expect(xhr.sentBody?.get('file')).toBe(file)

  xhr.status = 201
  xhr.responseText = JSON.stringify({ id: 'd1', filename: 'label.pdf', doc_kind: 'label' })
  xhr.onload?.()

  const doc = await promise
  expect(doc.id).toBe('d1')
})

test('uploadDocument surfaces the server rejection detail on a non-2xx response', async () => {
  MockXHR.instances = []
  vi.stubGlobal('XMLHttpRequest', MockXHR as unknown as typeof XMLHttpRequest)

  const file = new File(['hello'], 'huge.pdf', { type: 'application/pdf' })
  const promise = productsApi.uploadDocument({ file, docKind: 'other', productId: 'p1' })

  const xhr = MockXHR.instances[0]
  xhr.status = 400
  xhr.statusText = 'Bad Request'
  xhr.responseText = JSON.stringify({ detail: 'File exceeds the 20MB size limit' })
  xhr.onload?.()

  await expect(promise).rejects.toMatchObject({ status: 400, message: 'File exceeds the 20MB size limit' })
})
