import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { useAuth } from '../hooks/useAuth'

interface FormValues {
  username: string
  password: string
}

export default function LoginPage() {
  const { handleLogin } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<FormValues>()

  async function onSubmit(data: FormValues) {
    try {
      setError(null)
      await handleLogin(data.username, data.password)
    } catch {
      setError('Credenciales inválidas. Verificá tu usuario y contraseña.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-1">
          <h1 className="text-2xl font-semibold text-slate-900">Gestión de Minutas</h1>
          <p className="text-sm text-slate-500">Ingresá con tus credenciales</p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4 bg-white p-6 rounded-lg border border-slate-200 shadow-sm"
        >
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Usuario</label>
            <Input
              {...register('username', { required: true })}
              placeholder="usuario"
              autoComplete="username"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Contraseña</label>
            <Input
              {...register('password', { required: true })}
              type="password"
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded px-3 py-2">{error}</p>
          )}

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Ingresando...' : 'Ingresar'}
          </Button>
        </form>
      </div>
    </div>
  )
}
