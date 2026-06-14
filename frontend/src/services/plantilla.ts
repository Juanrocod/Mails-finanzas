// frontend/src/services/plantilla.ts
import { api } from './api'
import type { Plantilla } from '../types/domain'

export async function fetchPlantilla(): Promise<Plantilla> {
  const res = await api.get<Plantilla>('/plantilla')
  return res.data
}

export async function guardarPlantilla(texto: string): Promise<Plantilla> {
  const res = await api.patch<Plantilla>('/plantilla', { texto })
  return res.data
}
