import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileText, Send, FileEdit, Settings2, Upload, LogOut, KeyRound, ShieldCheck } from 'lucide-react'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Separator } from '../ui/separator'
import { cn } from '../../lib/utils'
import { fetchMinutas } from '../../services/minutas'
import { useAuth } from '../../hooks/useAuth'
import ExcelUploadModal from '../upload/ExcelUploadModal'
import ChangePasswordModal from '../profile/ChangePasswordModal'
import RegenerateTOTPModal from '../profile/RegenerateTOTPModal'
import type { EstadoMinuta } from '../../types/domain'

function useBadgeCount(estado: EstadoMinuta): number {
  const { data } = useQuery({
    queryKey: ['minutas', estado],
    queryFn: () => fetchMinutas(estado),
    staleTime: 30_000,
  })
  return data?.total ?? 0
}

function NavItem({
  to,
  label,
  icon: Icon,
  count,
}: {
  to: string
  label: string
  icon: React.ElementType
  count?: number
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'flex items-center justify-between px-3 py-2 rounded-md text-sm transition-colors',
          isActive
            ? 'bg-slate-100 text-slate-900 font-medium'
            : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
        )
      }
    >
      <span className="flex items-center gap-2">
        <Icon className="h-4 w-4 shrink-0" />
        {label}
      </span>
      {count != null && count > 0 && (
        <Badge variant="secondary" className="text-xs tabular-nums">
          {count}
        </Badge>
      )}
    </NavLink>
  )
}

export default function Sidebar() {
  const { handleLogout } = useAuth()
  const [uploadOpen, setUploadOpen] = useState(false)
  const [changePassOpen, setChangePassOpen] = useState(false)
  const [regenTOTPOpen, setRegenTOTPOpen] = useState(false)
  const borradores = useBadgeCount('BORRADOR')
  const enviados = useBadgeCount('ENVIADO')

  return (
    <>
      <aside className="w-60 h-screen flex flex-col bg-white border-r border-slate-200 shrink-0">
        <div className="px-4 py-5 border-b border-slate-100">
          <p className="text-sm font-semibold text-slate-900">Gestión de Minutas</p>
          <p className="text-xs text-slate-400 mt-0.5">Sistema bursátil CNV</p>
        </div>

        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          <NavItem to="/dashboard/borradores" label="Borradores" icon={FileText} count={borradores} />
          <NavItem to="/dashboard/enviados" label="Enviados" icon={Send} count={enviados} />
          <Separator className="my-2" />
          <NavItem to="/dashboard/plantilla" label="Plantilla Estándar" icon={FileEdit} />
          <NavItem to="/dashboard/config-dj" label="Config DJ" icon={Settings2} />
        </nav>

        <div className="p-3 border-t border-slate-100 space-y-2">
          <Button
            variant="outline"
            size="sm"
            className="w-full gap-2"
            onClick={() => setUploadOpen(true)}
          >
            <Upload className="h-3.5 w-3.5" />
            Subir Excel
          </Button>
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-semibold text-slate-600">
                MO
              </div>
              <span className="text-xs text-slate-600">Middle Office</span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setChangePassOpen(true)}
                title="Cambiar contraseña"
              >
                <KeyRound className="h-3.5 w-3.5 text-slate-400" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setRegenTOTPOpen(true)}
                title="Regenerar Authenticator"
              >
                <ShieldCheck className="h-3.5 w-3.5 text-slate-400" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={handleLogout}
                title="Cerrar sesión"
              >
                <LogOut className="h-3.5 w-3.5 text-slate-400" />
              </Button>
            </div>
          </div>
        </div>
      </aside>

      <ExcelUploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
      <ChangePasswordModal open={changePassOpen} onClose={() => setChangePassOpen(false)} />
      <RegenerateTOTPModal open={regenTOTPOpen} onClose={() => setRegenTOTPOpen(false)} />
    </>
  )
}
