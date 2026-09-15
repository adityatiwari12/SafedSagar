import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'
import { AuthProvider, useAuth } from './AuthContext'
import { authApi } from '../api/authApi'

vi.mock('../api/authApi', () => ({
  authApi: { register: vi.fn(), login: vi.fn(), me: vi.fn() },
}))

function Probe() {
  const { user, status, login, logout } = useAuth()
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="email">{user?.email ?? 'none'}</span>
      <button type="button" onClick={() => login('a@b.com', 'password123')}>
        login
      </button>
      <button type="button" onClick={() => logout()}>
        logout
      </button>
    </div>
  )
}

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
})

test('starts unauthenticated with no stored token', async () => {
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  )
  await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('unauthenticated'))
})

test('login stores token, fetches profile, exposes user', async () => {
  ;(authApi.login as ReturnType<typeof vi.fn>).mockResolvedValue({
    access_token: 'tok',
    token_type: 'bearer',
  })
  ;(authApi.me as ReturnType<typeof vi.fn>).mockResolvedValue({
    id: '1',
    email: 'a@b.com',
    role: 'user',
    jurisdiction_preference: null,
  })

  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  )
  await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('unauthenticated'))

  await act(async () => {
    await userEvent.click(screen.getByText('login'))
  })

  expect(screen.getByTestId('email').textContent).toBe('a@b.com')
  expect(localStorage.getItem('ipsakti_token')).toBe('tok')
})

test('restores session from stored token on mount', async () => {
  localStorage.setItem('ipsakti_token', 'tok')
  ;(authApi.me as ReturnType<typeof vi.fn>).mockResolvedValue({
    id: '1',
    email: 'a@b.com',
    role: 'user',
    jurisdiction_preference: null,
  })

  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  )

  await waitFor(() => expect(screen.getByTestId('email').textContent).toBe('a@b.com'))
})

test('logout clears user and stored token', async () => {
  ;(authApi.login as ReturnType<typeof vi.fn>).mockResolvedValue({
    access_token: 'tok',
    token_type: 'bearer',
  })
  ;(authApi.me as ReturnType<typeof vi.fn>).mockResolvedValue({
    id: '1',
    email: 'a@b.com',
    role: 'user',
    jurisdiction_preference: null,
  })

  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  )
  await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('unauthenticated'))
  await act(async () => {
    await userEvent.click(screen.getByText('login'))
  })
  await act(async () => {
    await userEvent.click(screen.getByText('logout'))
  })

  expect(screen.getByTestId('email').textContent).toBe('none')
  expect(localStorage.getItem('ipsakti_token')).toBeNull()
})
