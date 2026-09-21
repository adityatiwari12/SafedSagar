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
