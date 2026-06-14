import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import { Download, Search } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Skeleton } from '../components/ui/skeleton'
import { fetchAuditTrail, downloadAuditExcel } from '../services/audit'
import type { AccionAudit } from '../types/domain'

const ACCION_LABEL: Record<AccionAudit, string> = {
  CREADA: 'Creada',
  EDITADA: 'Texto editado',
  APROBADA: 'Aprobada',
  ENVIADA: 'Marcada como enviada',
  CONFIRMADA: 'Confirmación registrada',
  ALERTA_GENERADA: 'Alerta generada',
}

interface FormValues {
  ordenId: string
}

export default function AuditPage() {
  const [activeOrdenId, setActiveOrdenId] = useState<string | null>(null)

  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['audit', activeOrdenId],
    queryFn: () => fetchAuditTrail(activeOrdenId!),
    enabled: activeOrdenId !== null,
  })

  function onSubmit({ ordenId }: FormValues) {
    setActiveOrdenId(ordenId.trim())
  }

  async function handleExportExcel() {
    if (!activeOrdenId) return
    await downloadAuditExcel(activeOrdenId)
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Audit Trail</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Ingresá el ID de una orden para ver su historial de eventos.
          </p>
        </div>
        {activeOrdenId && data && data.length > 0 && (
          <Button variant="outline" size="sm" className="gap-2" onClick={handleExportExcel}>
            <Download className="h-3.5 w-3.5" />
            Exportar Excel
          </Button>
        )}
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="flex gap-2">
        <div className="flex-1 space-y-1">
          <Input
            id="ordenId"
            {...register('ordenId', { required: 'Ingresá el ID de la orden' })}
            placeholder="UUID de la orden (ej: 550e8400-e29b-41d4-a716-446655440000)"
            className="font-mono text-sm"
          />
          {errors.ordenId && (
            <p className="text-xs text-red-600">{errors.ordenId.message}</p>
          )}
        </div>
        <Button type="submit" size="sm" className="gap-2 shrink-0 self-start">
          <Search className="h-3.5 w-3.5" />
          Buscar
        </Button>
      </form>

      {isLoading && <Skeleton className="h-48 w-full rounded-lg" />}

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-700">
            No se encontró la orden o no hay eventos registrados. Verificá el ID.
          </p>
        </div>
      )}

      {data && data.length === 0 && (
        <p className="text-sm text-slate-400 text-center py-8">
          Sin eventos para esta orden.
        </p>
      )}

      {data && data.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Acción
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Fecha y hora
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  IP
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((event) => (
                <tr key={event.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-800">
                    {ACCION_LABEL[event.accion] ?? event.accion}
                  </td>
                  <td className="px-4 py-3 text-slate-600 tabular-nums">
                    {format(new Date(event.timestamp), 'dd/MM/yyyy HH:mm:ss', { locale: es })}
                  </td>
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs">
                    {event.ip_origen ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
