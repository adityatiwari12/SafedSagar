import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { RequireAuth } from './auth/RequireAuth'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import RolePlaceholderPage from './pages/RolePlaceholderPage'
import CasesPage from './pages/CasesPage'
import AdminPage from './pages/AdminPage'
import ChatPage from './chat/ChatPage'
import ClassificationWizard from './classify/ClassificationWizard'
import LandingPage from './landing/LandingPage'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
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
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
