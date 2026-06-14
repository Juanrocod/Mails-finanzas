import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import { ChevronDown } from 'lucide-react'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '../ui/collapsible'
import { Skeleton } from '../ui/skeleton'
import { fetchAuditTrail } from '../../services/audit'
import type { AccionAudit } from '../../types/domain'

const ACCION_LABEL: Record<AccionAudit, string> = {
  CREADA: 'Minuta creada',
  EDITADA: 'Texto editado',
  APROBADA: 'Aprobada',
  ENVIADA: 'Marcada como enviada',
  CONFIRMADA: 'Confirmación registrada',
  ALERTA_GENERADA: 'Alerta generada',
}

interface Props {
  ordenId: string
}

export default function AuditTrailSection({ ordenId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ['audit', ordenId],
    queryFn: () => fetchAuditTrail(ordenId),
  })

  return (
    <Collapsible>
      <CollapsibleTrigger className="flex items-center justify-between w-full text-sm font-medium text-slate-700 hover:text-slate-900 py-1 group">
        <span>Audit Trail</span>
        <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-data-[state=open]:rotate-180" />
      </CollapsibleTrigger>
      <CollapsibleContent className="pt-3">
        {isLoading && <Skeleton className="h-24 w-full rounded-md" />}
        {data && data.length === 0 && (
          <p className="text-xs text-slate-400">Sin eventos registrados.</p>
        )}
        {data && data.length > 0 && (
          <div className="space-y-3">
            {data.map((event) => (
              <div
                key={event.id}
                className="border-l-2 border-slate-200 pl-3 space-y-0.5"
              >
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-medium text-slate-700">
                    {ACCION_LABEL[event.accion] ?? event.accion}
                  </span>
                  <span className="text-xs text-slate-400">
                    {format(new Date(event.timestamp), 'dd/MM/yyyy HH:mm:ss', {
                      locale: es,
                    })}
                  </span>
                </div>
                {event.ip_origen && (
                  <p className="text-[11px] text-slate-400">IP: {event.ip_origen}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  )
}
