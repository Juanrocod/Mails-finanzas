// frontend/src/pages/ConfigDJPage.tsx
import { useState, useEffect } from 'react'
import { AlertTriangle } from 'lucide-react'
import { Textarea } from '../components/ui/textarea'
import { Button } from '../components/ui/button'
import { useConfigDJ, useGuardarConfigDJ } from '../hooks/useSession'

export default function ConfigDJPage() {
  const { data, isLoading } = useConfigDJ()
  const guardar = useGuardarConfigDJ()
  const [activa, setActiva] = useState(false)
  const [textoAlerta, setTextoAlerta] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) {
      setActiva(data.activa)
      setTextoAlerta(data.texto_alerta)
    }
  }, [data])

  async function handleGuardar() {
    try {
      await guardar.mutateAsync({ activa, texto_alerta: textoAlerta })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      // error silenciado
    }
  }

  const modificado = data
    ? activa !== data.activa || textoAlerta !== data.texto_alerta
    : false

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Configuración DJ</h2>
        <p className="text-sm text-slate-500 mt-1">
          Cuando la DJ está activa, se agrega el texto de alerta al final de cada minuta generada.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <div className="h-10 bg-slate-100 rounded animate-pulse" />
          <div className="h-32 bg-slate-100 rounded animate-pulse" />
        </div>
      ) : (
        <div className="space-y-4">
          {/* Toggle DJ activa */}
          <div className="flex items-center gap-3 p-4 border border-slate-200 rounded-lg">
            <button
              type="button"
              role="switch"
              aria-checked={activa}
              onClick={() => { setActiva(!activa); setSaved(false) }}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 ${
                activa ? 'bg-slate-800' : 'bg-slate-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  activa ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
            <div>
              <p className="text-sm font-medium text-slate-800">
                {activa ? 'DJ activa' : 'DJ inactiva'}
              </p>
              <p className="text-xs text-slate-500">
                {activa
                  ? 'El texto de alerta se incluirá en todas las minutas generadas'
                  : 'No se agrega ningún texto de DJ a las minutas'}
              </p>
            </div>
            {activa && <AlertTriangle className="h-4 w-4 text-amber-500 ml-auto shrink-0" />}
          </div>

          {/* Texto de alerta */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700 flex items-center gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
              Texto de alerta DJ
            </label>
            <Textarea
              value={textoAlerta}
              onChange={(e) => { setTextoAlerta(e.target.value); setSaved(false) }}
              rows={8}
              disabled={!activa}
              className="font-mono text-sm resize-none disabled:opacity-50"
              placeholder="Ingresá el texto que aparecerá en la sección DJ de cada minuta..."
            />
          </div>
        </div>
      )}

      <div className="flex items-center gap-3">
        <Button
          onClick={handleGuardar}
          disabled={guardar.isPending || !modificado}
        >
          {guardar.isPending ? 'Guardando...' : 'Guardar configuración'}
        </Button>
        {saved && (
          <span className="text-sm text-green-600">Guardado</span>
        )}
      </div>
    </div>
  )
}
