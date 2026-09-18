import { beforeEach, afterEach, expect, test, vi } from 'vitest'
import { productsApi } from '../api/productsApi'
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
