import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { authApi, RegisterOptions, UserProfile } from '../api/authApi'
import { ApiError } from '../api/http'

const TOKEN_KEY = 'ipsakti_token'

type Status = 'idle' | 'loading' | 'authenticated' | 'unauthenticated'

interface AuthContextValue {
  user: UserProfile | null
  status: Status
  login(email: string, password: string): Promise<UserProfile>
  register(email: string, password: string, options?: RegisterOptions): Promise<UserProfile>
  logout(): void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [status, setStatus] = useState<Status>('idle')

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      setStatus('unauthenticated')
      return
    }
    setStatus('loading')
    authApi
      .me(token)
      .then((profile) => {
        setUser(profile)
        setStatus('authenticated')
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY)
        setStatus('unauthenticated')
      })
  }, [])

  async function login(email: string, password: string): Promise<UserProfile> {
    const tokens = await authApi.login(email, password)
    localStorage.setItem(TOKEN_KEY, tokens.access_token)
    const profile = await authApi.me(tokens.access_token)
    setUser(profile)
    setStatus('authenticated')
    return profile
  }

  async function register(
    email: string,
    password: string,
    options?: RegisterOptions,
  ): Promise<UserProfile> {
    await authApi.register(email, password, options)
    return login(email, password)
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
    setStatus('unauthenticated')
  }

  return (
    <AuthContext.Provider value={{ user, status, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export { ApiError }
