import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import { getAccessToken } from '../../services/api'

export default function AppLayout() {
  useEffect(() => {
    function onBeforeUnload() {
      const token = getAccessToken()
      if (!token) return
      // fetch con keepalive garantiza que el browser completa la petición
      // aunque la página se esté descargando (F5, cerrar pestaña)
      fetch(`${import.meta.env.VITE_API_URL}/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        keepalive: true,
      })
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [])

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
