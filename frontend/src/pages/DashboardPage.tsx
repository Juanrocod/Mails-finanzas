import { useState } from 'react'
import { Skeleton } from '../components/ui/skeleton'
import MinutaCard from '../components/minutas/MinutaCard'
import MinutaDrawer from '../components/minutas/MinutaDrawer'
import { useMinutas } from '../hooks/useMinutas'
import type { EstadoMinuta } from '../types/domain'

const ESTADO_TITULO: Record<EstadoMinuta, string> = {
  BORRADOR: 'Borradores',
  APROBADO: 'Aprobados',
  ENVIADO: 'Enviados',
  CONFIRMADO: 'Confirmados',
  ALERTA: 'Alertas',
}

interface Props {
  estado: EstadoMinuta
}

export default function DashboardPage({ estado }: Props) {
  const { data, isLoading, isError } = useMinutas(estado)
  const [selectedOrdenId, setSelectedOrdenId] = useState<string | null>(null)
  const selectedOrden = data?.items.find((o) => o.id === selectedOrdenId) ?? null

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-baseline gap-3">
        <h2 className="text-xl font-semibold text-slate-900">
          {ESTADO_TITULO[estado]}
        </h2>
        {data && (
          <span className="text-sm text-slate-400">
            {data.total} {data.total === 1 ? 'orden' : 'órdenes'}
          </span>
        )}
      </div>

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-lg" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-700">
            Error al cargar las órdenes. Verificá tu conexión e intentá de nuevo.
          </p>
        </div>
      )}

      {data && data.items.length === 0 && !isLoading && (
        <div className="text-center py-16">
          <p className="text-sm text-slate-400">No hay órdenes en estado {estado}.</p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((orden) => (
            <MinutaCard
              key={orden.id}
              orden={orden}
              onClick={() => setSelectedOrdenId(orden.id)}
            />
          ))}
        </div>
      )}

      <MinutaDrawer
        orden={selectedOrden}
        onClose={() => setSelectedOrdenId(null)}
      />
    </div>
  )
}
