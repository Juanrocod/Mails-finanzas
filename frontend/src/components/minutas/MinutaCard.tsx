// frontend/src/components/minutas/MinutaCard.tsx
import type React from 'react'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import { AlertTriangle, PenLine } from 'lucide-react'
import { Badge } from '../ui/badge'
import { Card } from '../ui/card'
import { cn } from '../../lib/utils'
import type { Minuta } from '../../types/domain'

const ESTADO_BADGE: Record<string, string> = {
  BORRADOR: 'bg-slate-100 text-slate-700 hover:bg-slate-100',
  ENVIADO: 'bg-green-100 text-green-800 hover:bg-green-100',
  FILTRADA: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-100',
}

function fmtNum(val: number): string {
  if (val === -1) return 'N/A'
  if (Number.isInteger(val)) return val.toLocaleString('es-AR')
  return val.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

interface Props {
  minuta: Minuta
  onClick: () => void
}

export default function MinutaCard({ minuta, onClick }: Props) {
  const fechaFormateada = (() => {
    try {
      return format(new Date(minuta.fecha_operacion), 'dd/MM/yyyy HH:mm', { locale: es })
    } catch {
      return minuta.fecha_operacion
    }
  })()

  return (
    <Card
      role="button"
      tabIndex={0}
      onKeyDown={(e: React.KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      }}
      className="p-4 cursor-pointer hover:shadow-md transition-all select-none"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0 space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-slate-900 truncate max-w-[200px]">
              {minuta.cliente_nombre}
            </span>
            <Badge
              variant="secondary"
              className={cn(
                'text-xs font-semibold shrink-0',
                minuta.operacion === 'COMPRA'
                  ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100'
                  : 'bg-red-100 text-red-700 hover:bg-red-100'
              )}
            >
              {minuta.operacion}
            </Badge>
            {minuta.dj_aplicada && (
              <AlertTriangle
                className="h-3.5 w-3.5 text-amber-500 shrink-0"
                aria-label="Con Declaración Jurada"
              />
            )}
            {minuta.texto_editado && (
              <PenLine
                className="h-3.5 w-3.5 text-amber-500 shrink-0"
                aria-label="Texto editado manualmente"
              />
            )}
          </div>

          <p className="text-sm text-slate-700">
            {minuta.instrumento || '—'} — {minuta.moneda} {fmtNum(minuta.monto)}
          </p>

          <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap">
            <span>Comitente: {minuta.cuenta_comitente}</span>
            <span>·</span>
            <span>{fechaFormateada}</span>
          </div>
        </div>

        <Badge
          variant="secondary"
          className={cn(
            'text-xs shrink-0 self-start mt-0.5',
            ESTADO_BADGE[minuta.estado] ?? 'bg-slate-100 text-slate-700'
          )}
        >
          {minuta.estado}
        </Badge>
      </div>
    </Card>
  )
}
