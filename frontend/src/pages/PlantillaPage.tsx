// frontend/src/pages/PlantillaPage.tsx
import { useState, useEffect } from 'react'
import { Textarea } from '../components/ui/textarea'
import { Button } from '../components/ui/button'
import { usePlantilla, useGuardarPlantilla } from '../hooks/useSession'

export default function PlantillaPage() {
  const { data, isLoading } = usePlantilla()
  const guardar = useGuardarPlantilla()
  const [texto, setTexto] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) setTexto(data.texto)
  }, [data])

  async function handleGuardar() {
    try {
      await guardar.mutateAsync(texto)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      // error silenciado — el backend solo falla si no está autenticado
    }
  }

  const modificado = data ? texto !== data.texto : false

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Plantilla Estándar</h2>
        <p className="text-sm text-slate-500 mt-1">
          Texto base para las minutas de esta sesión. Los cambios se pierden al cerrar sesión.
        </p>
      </div>

      {isLoading ? (
        <div className="h-64 bg-slate-100 rounded animate-pulse" />
      ) : (
        <Textarea
          value={texto}
          onChange={(e) => { setTexto(e.target.value); setSaved(false) }}
          rows={18}
          className="font-mono text-sm resize-none"
          placeholder="Ingresá el texto de la plantilla estándar..."
        />
      )}

      <div className="flex items-center gap-3">
        <Button
          onClick={handleGuardar}
          disabled={guardar.isPending || !modificado}
        >
          {guardar.isPending ? 'Guardando...' : 'Guardar plantilla'}
        </Button>
        {saved && (
          <span className="text-sm text-green-600">Guardado</span>
        )}
      </div>
    </div>
  )
}
