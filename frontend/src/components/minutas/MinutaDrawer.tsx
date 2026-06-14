import { useEffect, useState } from 'react'
import { Copy, PenLine, ChevronDown } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '../ui/sheet'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Textarea } from '../ui/textarea'
import { Separator } from '../ui/separator'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '../ui/collapsible'
import { cn } from '../../lib/utils'
import AuditTrailSection from './AuditTrailSection'
import {
  useAprobarMinuta,
  useMarcarEnviada,
  useRegistrarConfirmacion,
  useEditarTexto,
} from '../../hooks/useMinutas'
import type { Orden } from '../../types/domain'

const ESTADO_BADGE: Record<string, string> = {
  BORRADOR: 'bg-slate-100 text-slate-700',
  APROBADO: 'bg-blue-100 text-blue-700',
  ENVIADO: 'bg-yellow-100 text-yellow-800',
  CONFIRMADO: 'bg-green-100 text-green-700',
  ALERTA: 'bg-red-100 text-red-700',
}

interface Props {
  orden: Orden | null
  onClose: () => void
}

export default function MinutaDrawer({ orden, onClose }: Props) {
  const [texto, setTexto] = useState('')
  const [mutationError, setMutationError] = useState<string | null>(null)
  const aprobar = useAprobarMinuta()
  const enviar = useMarcarEnviada()
  const confirmar = useRegistrarConfirmacion()
  const editarTexto = useEditarTexto()

  useEffect(() => {
    if (orden) {
      setTexto(orden.texto_minuta)
      setMutationError(null)
    }
  }, [orden?.id])

  const isLoading =
    aprobar.isPending ||
    enviar.isPending ||
    confirmar.isPending ||
    editarTexto.isPending

  async function handleGuardar() {
    if (!orden) return
    try {
      setMutationError(null)
      await editarTexto.mutateAsync({ ordenId: orden.id, texto })
    } catch {
      setMutationError('Error al guardar la edición. Intentá de nuevo.')
    }
  }

  async function handleAprobar() {
    if (!orden) return
    try {
      setMutationError(null)
      await aprobar.mutateAsync(orden.id)
      onClose()
    } catch {
      setMutationError('Error al aprobar la Minuta. Intentá de nuevo.')
    }
  }

  async function handleEnviar() {
    if (!orden) return
    try {
      setMutationError(null)
      await enviar.mutateAsync(orden.id)
      onClose()
    } catch {
      setMutationError('Error al marcar como enviada. Intentá de nuevo.')
    }
  }

  async function handleConfirmar() {
    if (!orden) return
    try {
      setMutationError(null)
      await confirmar.mutateAsync(orden.id)
      onClose()
    } catch {
      setMutationError('Error al registrar la confirmación. Intentá de nuevo.')
    }
  }

  async function handleCopiar() {
    if (!orden) return
    try {
      await navigator.clipboard.writeText(orden.texto_minuta)
    } catch {
      // clipboard unavailable (HTTP origin or WebView) — silently ignore for now
    }
  }

  const isBorrador = orden?.estado === 'BORRADOR'
  const textoModificado = texto !== orden?.texto_minuta

  return (
    <Sheet open={orden !== null} onOpenChange={(open) => { if (!open) onClose() }}>
      <SheetContent
        side="right"
        className="w-[600px] sm:max-w-[600px] p-0 flex flex-col overflow-hidden"
      >
        {orden && (
          <>
            <SheetHeader className="px-6 py-4 border-b border-slate-200 shrink-0">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <SheetTitle className="text-base font-semibold truncate">
                    {orden.cliente_nombre}
                  </SheetTitle>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Comitente: {orden.cuenta_comitente} · Cotapartista:{' '}
                    {orden.cuenta_cotapartista}
                  </p>
                </div>
                <Badge
                  variant="secondary"
                  className={cn('shrink-0 text-xs', ESTADO_BADGE[orden.estado])}
                >
                  {orden.estado}
                </Badge>
              </div>
            </SheetHeader>

            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              {/* Texto de la Minuta */}
              <section className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-slate-700">Texto de la Minuta</h3>
                  <div className="flex items-center gap-2">
                    {orden.texto_editado && (
                      <span className="flex items-center gap-1 text-xs text-amber-600">
                        <PenLine className="h-3 w-3" />
                        Editado
                      </span>
                    )}
                    {!isBorrador && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 gap-1.5 text-xs"
                        onClick={handleCopiar}
                      >
                        <Copy className="h-3.5 w-3.5" />
                        Copiar
                      </Button>
                    )}
                  </div>
                </div>
                {isBorrador ? (
                  <Textarea
                    value={texto}
                    onChange={(e) => setTexto(e.target.value)}
                    rows={14}
                    className="font-mono text-xs resize-none"
                  />
                ) : (
                  <pre className="text-xs font-mono bg-slate-50 border border-slate-200 rounded-md p-3 whitespace-pre-wrap break-words max-h-80 overflow-y-auto">
                    {orden.texto_minuta}
                  </pre>
                )}
              </section>

              {/* DJ section */}
              {orden.dj_aplicada && (
                <>
                  <Separator />
                  <Collapsible>
                    <CollapsibleTrigger className="flex items-center justify-between w-full text-sm font-medium text-slate-700 hover:text-slate-900 py-1 group">
                      <span>Declaración Jurada — {orden.dj_tipo ?? 'Incluida'}</span>
                      <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-data-[state=open]:rotate-180" />
                    </CollapsibleTrigger>
                    <CollapsibleContent className="pt-2">
                      <p className="text-xs text-slate-500">
                        La Declaración Jurada está incluida al final del texto de la Minuta.
                      </p>
                    </CollapsibleContent>
                  </Collapsible>
                </>
              )}

              {/* Acciones */}
              <Separator />
              <section className="space-y-3">
                <h3 className="text-sm font-medium text-slate-700">Acciones</h3>
                {mutationError && (
                  <p role="alert" className="text-xs text-red-600 bg-red-50 rounded px-2 py-1.5">
                    {mutationError}
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  {orden.estado === 'BORRADOR' && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleGuardar}
                        disabled={isLoading || !textoModificado}
                      >
                        Guardar edición
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleAprobar}
                        disabled={isLoading}
                      >
                        Aprobar
                      </Button>
                    </>
                  )}
                  {orden.estado === 'APROBADO' && (
                    <Button size="sm" onClick={handleEnviar} disabled={isLoading}>
                      Marcar como Enviada
                    </Button>
                  )}
                  {(orden.estado === 'ENVIADO' || orden.estado === 'ALERTA') && (
                    <Button size="sm" onClick={handleConfirmar} disabled={isLoading}>
                      Registrar Confirmación
                    </Button>
                  )}
                  {orden.estado === 'CONFIRMADO' && (
                    <p className="text-xs text-slate-500 py-1">
                      Orden confirmada. Sin acciones disponibles.
                    </p>
                  )}
                </div>
              </section>

              {/* Audit Trail */}
              <Separator />
              <AuditTrailSection ordenId={orden.id} />
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
