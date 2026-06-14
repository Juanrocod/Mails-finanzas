// frontend/src/services/minutas.ts
import { api } from './api'
import type { SessionMinutasResponse, Minuta, EstadoMinuta } from '../types/domain'

export async function fetchMinutas(estado: EstadoMinuta): Promise<SessionMinutasResponse> {
  const res = await api.get<SessionMinutasResponse>('/session/minutas', {
    params: { estado },
  })
  return res.data
}

export async function editarTexto(minutaId: string, texto_minuta: string): Promise<Minuta> {
  const res = await api.patch<Minuta>(`/session/minutas/${minutaId}/texto`, { texto_minuta })
  return res.data
}

export async function marcarEnviado(minutaId: string): Promise<Minuta> {
  const res = await api.patch<Minuta>(`/session/minutas/${minutaId}/enviado`)
  return res.data
}
