import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { regenerateTotp } from '../../services/auth'

interface Props {
  open: boolean
  onClose: () => void
}

type Step = 'confirm' | 'qr'

export default function RegenerateTOTPModal({ open, onClose }: Props) {
  const [step, setStep] = useState<Step>('confirm')
  const [totpCode, setTotpCode] = useState('')
  const [newTotpUri, setNewTotpUri] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function handleClose() {
    setStep('confirm')
    setTotpCode('')
    setNewTotpUri('')
    setError('')
    onClose()
  }

  async function handleConfirm(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await regenerateTotp(totpCode)
      setNewTotpUri(data.totp_uri)
      setStep('qr')
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setError('Código incorrecto')
      } else {
        setError('Error al regenerar. Intentá de nuevo.')
      }
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-6 w-full max-w-sm space-y-4">
        <h2 className="text-base font-semibold text-slate-900">Regenerar Authenticator</h2>

        {step === 'confirm' && (
          <>
            <p className="text-sm text-slate-500">
              Ingresá el código actual de tu Authenticator para confirmar que tenés acceso antes de generar uno nuevo.
            </p>
            <form onSubmit={handleConfirm} className="space-y-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Código actual (6 dígitos)</label>
                <Input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="123456"
                  required
                  autoComplete="one-time-code"
                />
              </div>
              {error && <p className="text-xs text-red-600">{error}</p>}
              <div className="flex gap-2">
                <Button type="button" variant="outline" className="flex-1" onClick={handleClose} disabled={loading}>
                  Cancelar
                </Button>
                <Button type="submit" className="flex-1" disabled={loading || totpCode.length !== 6}>
                  {loading ? 'Verificando...' : 'Continuar'}
                </Button>
              </div>
            </form>
          </>
        )}

        {step === 'qr' && (
          <div className="space-y-4">
            <p className="text-sm text-slate-500">
              Escaneá el nuevo QR con tu app de Authenticator. El código anterior ya no funcionará.
            </p>
            <div className="flex justify-center">
              <div className="p-3 bg-white border border-slate-200 rounded-lg">
                <QRCodeSVG value={newTotpUri} size={160} />
              </div>
            </div>
            <p className="text-xs text-slate-500 text-center">
              Código manual:
              <br />
              <span className="font-mono text-slate-700 break-all">
                {newTotpUri.split('secret=')[1]?.split('&')[0] ?? ''}
              </span>
            </p>
            <Button className="w-full" onClick={handleClose}>
              Listo
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
