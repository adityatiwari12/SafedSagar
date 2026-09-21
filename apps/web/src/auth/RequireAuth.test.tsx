import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { expect, test, vi } from 'vitest'
import { RequireAuth } from './RequireAuth'
import * as AuthContext from './AuthContext'
import { LanguageProvider } from '../i18n/LanguageContext'

function renderAt(path: string) {
  return render(
    <LanguageProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/login" element={<div>login page</div>} />
          <Route path="/placeholder" element={<div>placeholder page</div>} />
          <Route path="/cases" element={<div>cases page</div>} />
          <Route path="/dashboard" element={<div>dashboard page</div>} />
          <Route
            path="/"
            element={
              <RequireAuth allow={['user']}>
                <div>protected content</div>
              </RequireAuth>
            }
          />
        </Routes>
      </MemoryRouter>
    </LanguageProvider>,
  )
}

test('redirects to /login when unauthenticated', () => {
  vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
    user: null,
    status: 'unauthenticated',
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  })
  renderAt('/')
  expect(screen.getByText('login page')).toBeInTheDocument()
})

test('renders children when authenticated and role allowed', () => {
  vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
    user: {
      id: '1',
      email: 'a@b.com',
      role: 'user',
      persona: null,
      verification_status: 'approved',
      jurisdiction_preference: null,
    },
    status: 'authenticated',
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  })
  renderAt('/')
  expect(screen.getByText('protected content')).toBeInTheDocument()
})

test('redirects to role home (/dashboard) when role not allowed', () => {
  vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
    user: {
      id: '1',
      email: 'f@b.com',
      role: 'facilitator',
      persona: null,
      verification_status: 'approved',
      jurisdiction_preference: null,
    },
    status: 'authenticated',
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  })
  renderAt('/')
  expect(screen.getByText('dashboard page')).toBeInTheDocument()
})
