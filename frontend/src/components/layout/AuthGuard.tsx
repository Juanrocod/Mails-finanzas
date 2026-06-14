import { Navigate, Outlet } from 'react-router-dom'
import { getAccessToken } from '../../services/api'

export default function AuthGuard() {
  if (!getAccessToken()) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}
