import { Navigate } from 'react-router-dom'
import { ReactNode } from 'react'
import { useAuth } from './AuthContext'
import { UserProfile } from '../api/authApi'
import { roleHomePath } from './roleHome'

export function RequireAuth({
  children,
  allow,
}: {
  children: ReactNode
  allow?: Array<UserProfile['role']>
}) {
  const { user, status } = useAuth()

  if (status === 'loading' || status === 'idle') {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-ink-muted" role="status">
        Checking session…
      </div>
    )
  }
  if (status !== 'authenticated' || !user) return <Navigate to="/login" replace />
  if (allow && !allow.includes(user.role)) return <Navigate to={roleHomePath(user.role)} replace />

  return <>{children}</>
}
