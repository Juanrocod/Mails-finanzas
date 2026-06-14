import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import TwoFactorPage from './pages/TwoFactorPage'
import DashboardPage from './pages/DashboardPage'
import AuditPage from './pages/AuditPage'
import AppLayout from './components/layout/AppLayout'
import AuthGuard from './components/layout/AuthGuard'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/login/2fa" element={<TwoFactorPage />} />
      <Route element={<AuthGuard />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard/borradores" element={<DashboardPage estado="BORRADOR" />} />
          <Route path="/dashboard/aprobados" element={<DashboardPage estado="APROBADO" />} />
          <Route path="/dashboard/enviados" element={<DashboardPage estado="ENVIADO" />} />
          <Route path="/dashboard/confirmados" element={<DashboardPage estado="CONFIRMADO" />} />
          <Route path="/dashboard/alertas" element={<DashboardPage estado="ALERTA" />} />
          <Route path="/dashboard/audit" element={<AuditPage />} />
        </Route>
      </Route>
      <Route path="/" element={<Navigate to="/dashboard/borradores" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
