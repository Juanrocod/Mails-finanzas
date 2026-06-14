import { useNavigate } from 'react-router-dom'
import {
  login,
  verifyTotp,
  setPendingToken,
  getPendingToken,
  clearPendingToken,
} from '../services/auth'
import { setTokens, clearTokens, getAccessToken } from '../services/api'

export function useAuth() {
  const navigate = useNavigate()

  async function handleLogin(username: string, password: string): Promise<void> {
    const res = await login(username, password)
    setPendingToken(res.pending_token)
    navigate('/login/2fa')
  }

  async function handleVerify2fa(code: string): Promise<void> {
    const token = getPendingToken()
    if (!token) {
      navigate('/login')
      return
    }
    const res = await verifyTotp(token, code)
    clearPendingToken()
    setTokens(res.access_token, res.refresh_token)
    navigate('/dashboard/borradores')
  }

  function handleLogout(): void {
    clearTokens()
    navigate('/login')
  }

  function isAuthenticated(): boolean {
    return getAccessToken() !== null
  }

  return { handleLogin, handleVerify2fa, handleLogout, isAuthenticated }
}
