// frontend/src/pages/FiltrosMinutasPage.tsx
import { useState, useEffect } from 'react'
import { Filter, Plus, Trash2 } from 'lucide-react'
import { Button } from '../components/ui/button'
import { useConfigFiltros, usePatchConfigFiltros } from '../hooks/useSession'
import type { ReglaConfig, CampoRegla, OperadorRegla, ConfigFiltros } from '../types/domain'

const CAMPOS: { value: CampoRegla; label: string }[] = [
  { value: 'operacion', label: 'Operación' },
  { value: 'operador', label: 'Operador' },
  { value: 'origen', label: 'Origen' },
  { value: 'estado', label: 'Estado' },
  { value: 'moneda', label: 'Moneda' },
  { value: 'instrumento', label: 'Instrumento' },
  { value: 'cantidad', label: 'Cantidad' },
  { value: 'precio', label: 'Precio' },
  { value: 'monto', label: 'Monto' },
  { value: 'cantidad_operada', label: 'Cantidad operada' },
  { value: 'precio_operado', label: 'Precio operado' },
  { value: 'requiere_conformidad', label: 'Requiere conformidad' },
]

const OPERADORES: { value: OperadorRegla; label: string }[] = [
  { value: '=', label: '=' },
  { value: '!=', label: '!=' },
  { value: '>', label: '>' },
  { value: '<', label: '<' },
  { value: '>=', label: '>=' },
  { value: '<=', label: '<=' },
]

const REGLA_VACIA: ReglaConfig = { campo: 'operacion', operador: '=', valor: '' }

function reglasIguales(a: ReglaConfig[], b: ReglaConfig[]): boolean {
  if (a.length !== b.length) return false
  return a.every(
    (r, i) => r.campo === b[i].campo && r.operador === b[i].operador && r.valor === b[i].valor
  )
}

export default function FiltrosMinutasPage() {
  const { data, isLoading } = useConfigFiltros()
  const patch = usePatchConfigFiltros()

  const [reglas, setReglas] = useState<ReglaConfig[]>([])
  const [logica, setLogica] = useState<'AND' | 'OR'>('OR')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) {
      setReglas(data.reglas)
      setLogica(data.logica)
    }
  }, [data])

  const modificado = data
    ? logica !== data.logica || !reglasIguales(reglas, data.reglas)
    : false

  function agregarRegla() {
    setReglas((prev) => [...prev, { ...REGLA_VACIA }])
    setSaved(false)
  }

  function eliminarRegla(idx: number) {
    setReglas((prev) => prev.filter((_, i) => i !== idx))
    setSaved(false)
  }

  function actualizarRegla(idx: number, campo: keyof ReglaConfig, valor: string) {
    setReglas((prev) =>
      prev.map((r, i) => (i === idx ? { ...r, [campo]: valor } : r))
    )
    setSaved(false)
  }

  async function handleGuardar() {
    try {
      const config: ConfigFiltros = { reglas, logica }
      await patch.mutateAsync(config)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      // error silenciado
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Filtros de Minutas</h2>
        <p className="text-sm text-slate-500 mt-1">
          Define las reglas de exclusión. Las órdenes que cumplan las condiciones serán
          filtradas y no generarán minuta. La configuración se guarda en la base de datos
          y persiste entre sesiones.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <div className="h-10 bg-slate-100 rounded animate-pulse" />
          <div className="h-32 bg-slate-100 rounded animate-pulse" />
        </div>
      ) : (
        <div className="space-y-5">
          {/* Panel de reglas */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-slate-700">
                Reglas de exclusión
              </label>
              <Button variant="outline" size="sm" onClick={agregarRegla}>
                <Plus className="h-3.5 w-3.5 mr-1" />
                Agregar regla
              </Button>
            </div>

            {reglas.length === 0 && (
              <div className="flex items-center gap-2 p-4 border border-slate-200 rounded-lg bg-slate-50">
                <Filter className="h-4 w-4 text-slate-400 shrink-0" />
                <p className="text-sm text-slate-400 italic">
                  Sin reglas — todas las órdenes generarán minuta.
                </p>
              </div>
            )}

            {reglas.map((regla, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border border-slate-200"
              >
                <select
                  value={regla.campo}
                  onChange={(e) => actualizarRegla(idx, 'campo', e.target.value)}
                  className="text-sm border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400"
                >
                  {CAMPOS.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
                <select
                  value={regla.operador}
                  onChange={(e) => actualizarRegla(idx, 'operador', e.target.value)}
                  className="text-sm border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400 w-16"
                >
                  {OPERADORES.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <input
                  type="text"
                  value={regla.valor}
                  onChange={(e) => actualizarRegla(idx, 'valor', e.target.value)}
                  placeholder="valor"
                  className="flex-1 text-sm border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400"
                />
                <button
                  type="button"
                  onClick={() => eliminarRegla(idx)}
                  className="p-1.5 text-slate-400 hover:text-red-500 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}

            {/* Selector de lógica — solo visible cuando hay más de una regla */}
            {reglas.length > 1 && (
              <div className="flex items-center gap-3 pt-1">
                <span className="text-xs text-slate-500">Lógica entre reglas:</span>
                <div className="flex gap-2">
                  {(['OR', 'AND'] as const).map((l) => (
                    <button
                      key={l}
                      type="button"
                      onClick={() => { setLogica(l); setSaved(false) }}
                      className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                        logica === l
                          ? 'bg-slate-800 text-white border-slate-800'
                          : 'bg-white text-slate-600 border-slate-300 hover:border-slate-400'
                      }`}
                    >
                      {l === 'OR' ? 'OR — alguna regla' : 'AND — todas las reglas'}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="flex items-center gap-3">
        <Button
          onClick={handleGuardar}
          disabled={patch.isPending || !modificado}
        >
          {patch.isPending ? 'Guardando...' : 'Guardar configuración'}
        </Button>
        {saved && (
          <span className="text-sm text-green-600">Guardado</span>
        )}
      </div>
    </div>
  )
}
