import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import TwoFactorPage from './pages/TwoFactorPage'
import RegisterPage from './pages/RegisterPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import DashboardPage from './pages/DashboardPage'
import PlantillaPage from './pages/PlantillaPage'
import ConfigDJPage from './pages/ConfigDJPage'
import AppLayout from './components/layout/AppLayout'
import AuthGuard from './components/layout/AuthGuard'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/login/2fa" element={<TwoFactorPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route element={<AuthGuard />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard/borradores" element={<DashboardPage estado="BORRADOR" />} />
          <Route path="/dashboard/enviados" element={<DashboardPage estado="ENVIADO" />} />
          <Route path="/dashboard/plantilla" element={<PlantillaPage />} />
          <Route path="/dashboard/config-dj" element={<ConfigDJPage />} />
        </Route>
      </Route>
      <Route path="/" element={<Navigate to="/dashboard/borradores" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
