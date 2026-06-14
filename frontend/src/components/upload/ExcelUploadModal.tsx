import { useRef, useState } from 'react'
import { Upload } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'
import { Button } from '../ui/button'
import { cn } from '../../lib/utils'
import { uploadExcel } from '../../services/upload'
import type { UploadResponse, EstadoMinuta, SessionMinutasResponse } from '../../types/domain'

type Step = 'select' | 'warning' | 'preview' | 'uploading' | 'done'

interface Props {
  open: boolean
  onClose: () => void
}

export default function ExcelUploadModal({ open, onClose }: Props) {
  const qc = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const [step, setStep] = useState<Step>('select')
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<UploadResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [pendingBorradores, setPendingBorradores] = useState(0)

  function reset() {
    setStep('select')
    setFile(null)
    setResult(null)
    setError(null)
    setPendingBorradores(0)
  }

  function handleClose() {
    reset()
    onClose()
  }

  function selectFile(f: File) {
    if (!f.name.match(/\.(xlsx|xls)$/i)) {
      setError('Solo se aceptan archivos .xlsx o .xls')
      return
    }
    setFile(f)
    setError(null)
    const cached = qc.getQueryData<SessionMinutasResponse>(['minutas', 'BORRADOR' as EstadoMinuta])
    const count = cached?.total ?? 0
    if (count > 0) {
      setPendingBorradores(count)
      setStep('warning')
    } else {
      setStep('preview')
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setIsDragOver(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) selectFile(dropped)
  }

  async function handleUpload() {
    if (!file) return
    setStep('uploading')
    try {
      const res = await uploadExcel(file)
      setResult(res)
      qc.invalidateQueries({ queryKey: ['minutas', 'BORRADOR' as EstadoMinuta] })
      setStep('done')
    } catch {
      setError('Error al procesar el archivo. Verificá el formato e intentá de nuevo.')
      setStep('preview')
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) handleClose() }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Subir Excel de Operaciones</DialogTitle>
        </DialogHeader>

        {step === 'select' && (
          <div className="space-y-4">
            <div
              className={cn(
                'border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors',
                isDragOver
                  ? 'border-slate-400 bg-slate-50'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
              )}
              onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
            >
              <Upload className="h-8 w-8 mx-auto text-slate-300 mb-3" />
              <p className="text-sm text-slate-600 font-medium">
                Arrastrá el archivo o hacé click para seleccionar
              </p>
              <p className="text-xs text-slate-400 mt-1">Solo .xlsx o .xls</p>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) selectFile(f)
                e.target.value = ''
              }}
            />
            {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
          </div>
        )}

        {step === 'warning' && (
          <div className="space-y-4">
            <p className="text-sm text-slate-800">
              Tenés {pendingBorradores}{' '}
              {pendingBorradores === 1 ? 'mail sin enviar' : 'mails sin enviar'}. Si subís este
              archivo, se perderán. ¿Querés continuar?
            </p>
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => { setFile(null); setPendingBorradores(0); setStep('select') }}
              >
                No
              </Button>
              <Button onClick={() => setStep('preview')}>Sí</Button>
            </div>
          </div>
        )}

        {step === 'preview' && file && (
          <div className="space-y-4">
            <div className="bg-slate-50 rounded-md p-3 border border-slate-200">
              <p className="text-sm font-medium text-slate-800">{file.name}</p>
              <p className="text-xs text-slate-500 mt-0.5">
                {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
            <p className="text-sm text-slate-600">
              El archivo será procesado y se generarán las Minutas en estado Borrador.
            </p>
            {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => { setFile(null); setError(null); setStep('select') }}
              >
                Cambiar archivo
              </Button>
              <Button onClick={handleUpload}>Procesar</Button>
            </div>
          </div>
        )}

        {step === 'uploading' && (
          <div className="py-10 text-center space-y-3">
            <div className="h-8 w-8 mx-auto border-2 border-slate-200 border-t-slate-700 rounded-full animate-spin" />
            <p className="text-sm text-slate-600">Procesando archivo...</p>
          </div>
        )}

        {step === 'done' && result && (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-md p-4">
              <p className="text-sm font-semibold text-green-800">
                {result.ordenes_validas}{' '}
                {result.ordenes_validas === 1 ? 'Minuta generada' : 'Minutas generadas'} en
                Borradores
              </p>
              <p className="text-xs text-green-700 mt-0.5">
                Total procesadas: {result.total_ordenes} · Con errores:{' '}
                {result.ordenes_con_error}
              </p>
            </div>

            {result.errors.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-slate-700">Errores por fila:</p>
                <div className="max-h-36 overflow-y-auto space-y-1">
                  {result.errors.map((err) => (
                    <div
                      key={err.fila}
                      className="text-xs text-red-700 bg-red-50 rounded px-2 py-1 border border-red-100"
                    >
                      Fila {err.fila}: {err.mensaje}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Button className="w-full" onClick={handleClose}>
              Cerrar
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
