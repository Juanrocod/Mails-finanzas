import { useState, useEffect, useRef } from 'react'
import { AlertTriangle, Plus, Trash2 } from 'lucide-react'
import { Textarea } from '../components/ui/textarea'
import { Button } from '../components/ui/button'
import { useConfigDJ, useGuardarConfigDJ } from '../hooks/useSession'
import type { CampoRegla, OperadorRegla } from '../types/domain'

const CAMPOS: { value: CampoRegla; label: string }[] = [
  { value: 'operacion',            label: 'Operación' },
  { value: 'operador',             label: 'Operador' },
  { value: 'origen',               label: 'Origen' },
  { value: 'estado',               label: 'Estado' },
  { value: 'moneda',               label: 'Moneda' },
  { value: 'instrumento',          label: 'Instrumento' },
  { value: 'cantidad',             label: 'Cantidad' },
  { value: 'precio',               label: 'Precio' },
  { value: 'monto',                label: 'Monto' },
  { value: 'cantidad_operada',     label: 'Cantidad Operada' },
  { value: 'precio_operado',       label: 'Precio Operado' },
  { value: 'requiere_conformidad', label: 'Requiere Conformidad' },
]

const OPERADORES: { value: OperadorRegla; label: string }[] = [
  { value: '>=', label: '>=' },
  { value: '<=', label: '<=' },
  { value: '>',  label: '>'  },
  { value: '<',  label: '<'  },
  { value: '=',  label: '='  },
  { value: '!=', label: '!=' },
]

const DJ_VARIABLES = [
  '{cliente_nombre}', '{cuenta_comitente}', '{cuenta_cotapartista}',
  '{operacion}', '{instrumento}', '{cantidad}', '{precio}', '{monto}',
  '{moneda}', '{fecha_operacion}', '{fecha_liquidacion}', '{estado}',
  '{asesor}', '{operador}', '{origen}', '{id_orden}',
]

const REGLA_VACIA: { campo: CampoRegla; operador: OperadorRegla; valor: string } = {
  campo: 'cantidad', operador: '>=', valor: '',
}

function reglasIguales(
  a: { campo: CampoRegla; operador: OperadorRegla; valor: string }[],
  b: { campo: CampoRegla; operador: OperadorRegla; valor: string }[]
): boolean {
  if (a.length !== b.length) return false
  return a.every((r, i) => r.campo === b[i].campo && r.operador === b[i].operador && r.valor === b[i].valor)
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 ${
        checked ? 'bg-slate-800' : 'bg-slate-200'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  )
}

export default function ConfigDJPage() {
  const { data, isLoading } = useConfigDJ()
  const guardar = useGuardarConfigDJ()
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const [activa, setActiva] = useState(false)
  const [activarSiRequiereConformidad, setActivarSiRequiereConformidad] = useState(true)
  const [reglas, setReglas] = useState<{ campo: CampoRegla; operador: OperadorRegla; valor: string }[]>([])
  const [logica, setLogica] = useState<'AND' | 'OR'>('OR')
  const [incluirTexto, setIncluirTexto] = useState(false)
  const [textoAlerta, setTextoAlerta] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) {
      setActiva(data.activa)
      setActivarSiRequiereConformidad(data.activar_si_requiere_conformidad)
      setReglas(data.reglas)
      setLogica(data.logica)
      setIncluirTexto(data.incluir_texto_en_minuta)
      setTextoAlerta(data.texto_alerta)
    }
  }, [data])

  const modificado = data
    ? activa !== data.activa ||
      activarSiRequiereConformidad !== data.activar_si_requiere_conformidad ||
      logica !== data.logica ||
      incluirTexto !== data.incluir_texto_en_minuta ||
      textoAlerta !== data.texto_alerta ||
      !reglasIguales(reglas, data.reglas)
    : false

  function insertarVariable(variable: string) {
    const el = textareaRef.current
    if (!el) return
    const start = el.selectionStart
    const end = el.selectionEnd
    const nuevo = textoAlerta.slice(0, start) + variable + textoAlerta.slice(end)
    setTextoAlerta(nuevo)
    setSaved(false)
    requestAnimationFrame(() => {
      el.focus()
      const pos = start + variable.length
      el.setSelectionRange(pos, pos)
    })
  }

  function agregarRegla() {
    setReglas((prev) => [...prev, { ...REGLA_VACIA }])
    setSaved(false)
  }

  function eliminarRegla(idx: number) {
    setReglas((prev) => prev.filter((_, i) => i !== idx))
    setSaved(false)
  }

  function actualizarRegla(idx: number, campo: 'campo' | 'operador' | 'valor', valor: string) {
    setReglas((prev) => prev.map((r, i) => (i === idx ? { ...r, [campo]: valor } : r)))
    setSaved(false)
  }

  async function handleGuardar() {
    try {
      await guardar.mutateAsync({
        activa,
        activar_si_requiere_conformidad: activarSiRequiereConformidad,
        reglas,
        logica,
        incluir_texto_en_minuta: incluirTexto,
        texto_alerta: textoAlerta,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      // error silenciado
    }
  }

  const disabled = !activa

  return (
    <div className="max-w-2xl mx-auto pb-24">
      {/* Encabezado */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-slate-900">Configuración DJ</h2>
        <p className="text-sm text-slate-500 mt-1">
          Define las condiciones bajo las cuales una operación requiere Declaración Jurada.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <div className="h-16 bg-slate-100 rounded-lg animate-pulse" />
          <div className="h-32 bg-slate-100 rounded-lg animate-pulse" />
          <div className="h-48 bg-slate-100 rounded-lg animate-pulse" />
        </div>
      ) : (
        <div className="space-y-5">

          {/* ── Sección 1: Toggle maestro ── */}
          <div className="flex items-center gap-3 p-4 border border-slate-200 rounded-lg">
            <Toggle checked={activa} onChange={() => { setActiva(!activa); setSaved(false) }} />
            <div className="flex-1">
              <p className="text-sm font-medium text-slate-800">
                {activa ? 'DJ activada' : 'DJ desactivada'}
              </p>
              <p className="text-xs text-slate-500">
                {activa
                  ? 'Se evaluarán las condiciones configuradas abajo en cada minuta generada'
                  : 'No se detectará ni avisará ninguna condición de DJ'}
              </p>
            </div>
            {activa && <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />}
          </div>

          {/* ── Sección 2: Activación automática ── */}
          <div className={`border border-slate-200 rounded-lg overflow-hidden transition-opacity ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
              <p className="text-sm font-semibold text-slate-700">Activación automática</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Condición que la plataforma bursátil ya indica en el Excel.
              </p>
            </div>
            <div className="flex items-center gap-3 p-4">
              <Toggle
                checked={activarSiRequiereConformidad}
                onChange={() => { setActivarSiRequiereConformidad(!activarSiRequiereConformidad); setSaved(false) }}
              />
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-800">
                  Activar DJ si la operación requiere conformidad
                </p>
                <p className="text-xs text-slate-500">
                  Cuando la plataforma marca "RequiereConformidad = 1", la DJ se dispara automáticamente sin evaluar las reglas de abajo.
                </p>
              </div>
            </div>
          </div>

          {/* ── Sección 3: Condiciones adicionales ── */}
          <div className={`border border-slate-200 rounded-lg overflow-hidden transition-opacity ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-700">Condiciones adicionales</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  Reglas manuales para detectar operaciones que requieren DJ.
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={agregarRegla}>
                <Plus className="h-3.5 w-3.5 mr-1" />
                Agregar regla
              </Button>
            </div>

            <div className="p-4 space-y-3">
              {reglas.length === 0 ? (
                <p className="text-sm text-slate-400 italic text-center py-4">
                  Sin reglas manuales — solo se usará la activación automática de arriba.
                </p>
              ) : (
                <>
                  {reglas.map((regla, idx) => (
                    <div key={idx} className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border border-slate-200">
                      <select
                        value={regla.campo}
                        onChange={(e) => actualizarRegla(idx, 'campo', e.target.value)}
                        className="text-sm border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400"
                      >
                        {CAMPOS.map((c) => (
                          <option key={c.value} value={c.value}>{c.label}</option>
                        ))}
                      </select>
                      <select
                        value={regla.operador}
                        onChange={(e) => actualizarRegla(idx, 'operador', e.target.value)}
                        className="text-sm border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400 w-16"
                      >
                        {OPERADORES.map((o) => (
                          <option key={o.value} value={o.value}>{o.label}</option>
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
                            {l === 'OR' ? 'Cualquiera se cumple (OR)' : 'Todas se cumplen (AND)'}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* ── Sección 4: Texto de DJ en el mail ── */}
          <div className={`border border-slate-200 rounded-lg overflow-hidden transition-opacity ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-700">Texto de Declaración Jurada en el mail</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  Cuando está activo, este texto se agrega automáticamente al cuerpo de la minuta.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Incluir en el mail</span>
                <Toggle
                  checked={incluirTexto}
                  onChange={() => { setIncluirTexto(!incluirTexto); setSaved(false) }}
                />
              </div>
            </div>

            {incluirTexto && (
              <div className="p-4 space-y-3">
                <div className="flex flex-wrap gap-1.5">
                  {DJ_VARIABLES.map((v) => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => insertarVariable(v)}
                      className="px-2 py-0.5 text-xs font-mono bg-slate-100 hover:bg-slate-200 text-slate-700 rounded border border-slate-200 transition-colors"
                    >
                      {v}
                    </button>
                  ))}
                </div>
                <Textarea
                  ref={textareaRef}
                  value={textoAlerta}
                  onChange={(e) => { setTextoAlerta(e.target.value); setSaved(false) }}
                  rows={6}
                  className="font-mono text-sm resize-none"
                  placeholder="Ej: El cliente {cliente_nombre} debe presentar Declaración Jurada por operación de {cantidad} títulos de {instrumento}..."
                />
              </div>
            )}
          </div>

        </div>
      )}

      {/* ── Botón sticky ── */}
      <div className="fixed bottom-0 left-60 right-0 bg-white border-t border-slate-200 px-6 py-3 flex items-center gap-3">
        <Button onClick={handleGuardar} disabled={guardar.isPending || !modificado}>
          {guardar.isPending ? 'Guardando...' : 'Guardar configuración'}
        </Button>
        {saved && <span className="text-sm text-green-600">Guardado ✓</span>}
        {modificado && !saved && (
          <span className="text-xs text-slate-400">Tenés cambios sin guardar</span>
        )}
      </div>
    </div>
  )
}
