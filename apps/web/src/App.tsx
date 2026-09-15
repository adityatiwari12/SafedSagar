import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { RequireAuth } from './auth/RequireAuth'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import RolePlaceholderPage from './pages/RolePlaceholderPage'
import ChatPage from './chat/ChatPage'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
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
          path="/"
          element={
            <RequireAuth allow={['user']}>
              <ChatPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
