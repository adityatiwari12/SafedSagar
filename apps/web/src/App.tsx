import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { RequireAuth } from './auth/RequireAuth'
import { LanguageProvider } from './i18n/LanguageContext'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import RolePlaceholderPage from './pages/RolePlaceholderPage'
import CasesPage from './pages/CasesPage'
import AdminPage from './pages/AdminPage'
import DashboardPage from './pages/DashboardPage'
import FeaturePlaceholderPage from './pages/FeaturePlaceholderPage'
import ChatPage from './chat/ChatPage'
import ClassificationWizard from './classify/ClassificationWizard'
import LandingPage from './landing/LandingPage'
import ProductsListPage from './products/ProductsListPage'
import ProductDetailPage from './products/ProductDetailPage'
import IpOpportunitiesPage from './research/IpOpportunitiesPage'
import TkAbsExplorerPage from './research/TkAbsExplorerPage'
import PriorArtPage from './research/PriorArtPage'

const PLANNED = [
  '/regulatory',
  '/documents',
  '/assessments',
  '/expert-assistance',
  '/reports',
  '/communication',
  '/sources',
  '/organisations',
  '/products-admin',
  '/knowledge-base',
  '/ai-quality',
  '/analytics',
  '/languages',
  '/jurisdictions',
  '/audit-logs',
  '/security',
] as const

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/dashboard"
            element={
              <RequireAuth>
                <DashboardPage />
              </RequireAuth>
            }
          />
          <Route
            path="/placeholder"
            element={
              <RequireAuth>
                <RolePlaceholderPage />
              </RequireAuth>
            }
          />
          <Route
            path="/ask"
            element={
              <RequireAuth allow={['user']}>
                <ChatPage />
              </RequireAuth>
            }
          />
          <Route
            path="/classify"
            element={
              <RequireAuth allow={['user']}>
                <ClassificationWizard />
              </RequireAuth>
            }
          />
          <Route
            path="/products"
            element={
              <RequireAuth allow={['user']}>
                <ProductsListPage />
              </RequireAuth>
            }
          />
          <Route
            path="/products/:id"
            element={
              <RequireAuth allow={['user']}>
                <ProductDetailPage />
              </RequireAuth>
            }
          />
          <Route
            path="/ip-strategy"
            element={
              <RequireAuth allow={['user']}>
                <IpOpportunitiesPage />
              </RequireAuth>
            }
          />
          <Route
            path="/tk-abs"
            element={
              <RequireAuth allow={['user']}>
                <TkAbsExplorerPage />
              </RequireAuth>
            }
          />
          <Route
            path="/prior-art"
            element={
              <RequireAuth allow={['user']}>
                <PriorArtPage />
              </RequireAuth>
            }
          />
          <Route
            path="/cases"
            element={
              <RequireAuth allow={['facilitator', 'regulatory_expert', 'admin']}>
                <CasesPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin"
            element={
              <RequireAuth allow={['admin']}>
                <AdminPage />
              </RequireAuth>
            }
          />
          {PLANNED.map((path) => (
            <Route
              key={path}
              path={path}
              element={
                <RequireAuth>
                  <FeaturePlaceholderPage />
                </RequireAuth>
              }
            />
          ))}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </LanguageProvider>
  )
}
