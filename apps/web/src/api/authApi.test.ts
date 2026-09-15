import { beforeEach, afterEach, expect, test, vi } from 'vitest'
import { authApi } from './authApi'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
})
afterEach(() => {
  vi.unstubAllGlobals()
})

test('register posts email and password as JSON', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 201,
    json: async () => ({
      id: '1',
      email: 'a@b.com',
      role: 'user',
      jurisdiction_preference: null,
    }),
  })

  const user = await authApi.register('a@b.com', 'password123')

  expect(user.email).toBe('a@b.com')
  const [url, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/auth/register')
  expect(JSON.parse(init.body)).toEqual({ email: 'a@b.com', password: 'password123' })
})

test('login posts form-encoded username/password and returns tokens', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ access_token: 'tok', token_type: 'bearer' }),
  })

  const tokens = await authApi.login('a@b.com', 'password123')

  expect(tokens.access_token).toBe('tok')
  const [url, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect(url).toContain('/auth/login')
  expect(init.body).toBeInstanceOf(URLSearchParams)
  expect((init.body as URLSearchParams).get('username')).toBe('a@b.com')
  expect((init.body as URLSearchParams).get('password')).toBe('password123')
})

test('me sends bearer token', async () => {
  ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      id: '1',
      email: 'a@b.com',
      role: 'user',
      jurisdiction_preference: null,
    }),
  })

  await authApi.me('tok')

  const [, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
  expect((init.headers as Headers).get('Authorization')).toBe('Bearer tok')
})
