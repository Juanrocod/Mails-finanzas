// frontend/src/components/minutas/MinutaDrawer.tsx
import { useEffect, useState } from 'react'
import { Copy, PenLine, ChevronDown, AlertTriangle } from 'lucide-react'
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
import { useMarcarEnviado, useEditarTexto } from '../../hooks/useMinutas'
import type { Minuta } from '../../types/domain'

const ESTADO_BADGE: Record<string, string> = {
  BORRADOR: 'bg-slate-100 text-slate-700',
  ENVIADO: 'bg-yellow-100 text-yellow-800',
}

interface Props {
  minuta: Minuta | null
  onClose: () => void
}

export default function MinutaDrawer({ minuta, onClose }: Props) {
  const [texto, setTexto] = useState('')
  const [mutationError, setMutationError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const marcarEnviado = useMarcarEnviado()
  const editarTexto = useEditarTexto()

  useEffect(() => {
    if (minuta) {
      setTexto(minuta.texto_minuta)
      setMutationError(null)
      setCopied(false)
    }
  }, [minuta?.id])

  const isLoading = marcarEnviado.isPending || editarTexto.isPending
  const isBorrador = minuta?.estado === 'BORRADOR'
  const textoModificado = texto !== minuta?.texto_minuta

  async function handleGuardar() {
    if (!minuta) return
    try {
      setMutationError(null)
      await editarTexto.mutateAsync({ minutaId: minuta.id, texto })
    } catch {
      setMutationError('Error al guardar la edición. Intentá de nuevo.')
    }
  }

  async function handleEnviado() {
    if (!minuta) return
    try {
      setMutationError(null)
      await marcarEnviado.mutateAsync(minuta.id)
      onClose()
    } catch {
      setMutationError('Error al marcar como enviada. Intentá de nuevo.')
    }
  }

  async function handleCopiar() {
    const textToCopy = isBorrador ? texto : (minuta?.texto_minuta ?? '')
    try {
      await navigator.clipboard.writeText(textToCopy)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard unavailable — silently ignore
    }
  }

  return (
    <Sheet open={minuta !== null} onOpenChange={(open) => { if (!open) onClose() }}>
      <SheetContent
        side="right"
        className="w-[600px] sm:max-w-[600px] p-0 flex flex-col overflow-hidden"
      >
        {minuta && (
          <>
            <SheetHeader className="px-6 py-4 border-b border-slate-200 shrink-0">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <SheetTitle className="text-base font-semibold truncate">
                    {minuta.cliente_nombre}
                  </SheetTitle>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Comitente: {minuta.cuenta_comitente} · Cotapartista:{' '}
                    {minuta.cuenta_cotapartista}
                  </p>
                </div>
                <Badge
                  variant="secondary"
                  className={cn('shrink-0 text-xs', ESTADO_BADGE[minuta.estado])}
                >
                  {minuta.estado}
                </Badge>
              </div>
            </SheetHeader>

            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              {/* Texto de la Minuta */}
              <section className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-slate-700">Texto de la Minuta</h3>
                  <div className="flex items-center gap-2">
                    {minuta.texto_editado && (
                      <span className="flex items-center gap-1 text-xs text-amber-600">
                        <PenLine className="h-3 w-3" />
                        Editado
                      </span>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 gap-1.5 text-xs"
                      onClick={handleCopiar}
                    >
                      <Copy className="h-3.5 w-3.5" />
                      {copied ? 'Copiado' : 'Copiar contenido'}
                    </Button>
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
                    {minuta.texto_minuta}
                  </pre>
                )}
              </section>

              {/* DJ section */}
              {minuta.dj_aplicada && minuta.dj_texto && (
                <>
                  <Separator />
                  <Collapsible>
                    <CollapsibleTrigger className="flex items-center justify-between w-full text-sm font-medium text-slate-700 hover:text-slate-900 py-1 group">
                      <span className="flex items-center gap-1.5">
                        <AlertTriangle className="h-4 w-4 text-amber-500" />
                        Declaración Jurada incluida
                      </span>
                      <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-data-[state=open]:rotate-180" />
                    </CollapsibleTrigger>
                    <CollapsibleContent className="pt-2">
                      <pre className="text-xs text-slate-600 bg-amber-50 border border-amber-100 rounded p-2 whitespace-pre-wrap">
                        {minuta.dj_texto}
                      </pre>
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
                  {isBorrador && (
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
                        onClick={handleEnviado}
                        disabled={isLoading}
                      >
                        Enviado
                      </Button>
                    </>
                  )}
                  {minuta.estado === 'ENVIADO' && (
                    <p className="text-xs text-slate-500 py-1">
                      Minuta enviada. Podés copiar el contenido si necesitás reenviar.
                    </p>
                  )}
                </div>
              </section>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
