import { api } from './api'
import type { DashboardPage, Orden, EstadoMinuta } from '../types/domain'

const ESTADO_SLUG: Record<EstadoMinuta, string> = {
  BORRADOR: 'borradores',
  APROBADO: 'aprobados',
  ENVIADO: 'enviados',
  CONFIRMADO: 'confirmados',
  ALERTA: 'alertas',
}

export async function fetchMinutas(
  estado: EstadoMinuta,
  page = 1,
  size = 50
): Promise<DashboardPage> {
  const res = await api.get<DashboardPage>(`/dashboard/${ESTADO_SLUG[estado]}`, {
    params: { page, size },
  })
  return res.data
}

export async function editarTexto(
  ordenId: string,
  texto_minuta: string
): Promise<Orden> {
  const res = await api.patch<Orden>(`/orders/${ordenId}/text`, { texto_minuta })
  return res.data
}

export async function aprobarMinuta(ordenId: string): Promise<Orden> {
  const res = await api.post<Orden>(`/orders/${ordenId}/approve`)
  return res.data
}

export async function marcarEnviada(ordenId: string): Promise<Orden> {
  const res = await api.post<Orden>(`/orders/${ordenId}/send`)
  return res.data
}

export async function registrarConfirmacion(ordenId: string): Promise<Orden> {
  const res = await api.post<Orden>(`/orders/${ordenId}/confirm`)
  return res.data
}
