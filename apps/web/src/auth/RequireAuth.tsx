import { Navigate, useLocation } from 'react-router-dom'
import { ReactNode } from 'react'
import { useAuth } from './AuthContext'
import { UserProfile } from '../api/authApi'
import { roleHomePath } from './roleHome'
import { useLanguage } from '../i18n/LanguageContext'

export function RequireAuth({
  children,
  allow,
}: {
  children: ReactNode
  allow?: Array<UserProfile['role']>
}) {
  const { user, status } = useAuth()
  const location = useLocation()
  const { t } = useLanguage()

  if (status === 'loading' || status === 'idle') {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-ink-muted" role="status">
        {t('chat.checkingSession')}
      </div>
    )
  }
  if (status !== 'authenticated' || !user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: `${location.pathname}${location.search}`,
          ...(typeof location.state === 'object' && location.state ? location.state : {}),
        }}
      />
    )
  }
  if (allow && !allow.includes(user.role)) return <Navigate to={roleHomePath(user.role)} replace />

  return <>{children}</>
}
