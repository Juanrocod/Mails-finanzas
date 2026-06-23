// frontend/src/services/configDJ.ts
import { api } from './api'
import type { ConfigDJ } from '../types/domain'

export async function fetchAllConfigDJ(): Promise<ConfigDJ[]> {
  const res = await api.get<ConfigDJ[]>('/config/dj')
  return res.data
}

export async function crearConfigDJ(config: ConfigDJ): Promise<ConfigDJ> {
  const res = await api.post<ConfigDJ>('/config/dj', config)
  return res.data
}

export async function actualizarConfigDJ(id: number, config: ConfigDJ): Promise<ConfigDJ> {
  const res = await api.patch<ConfigDJ>(`/config/dj/${id}`, config)
  return res.data
}

export async function eliminarConfigDJ(id: number): Promise<void> {
  await api.delete(`/config/dj/${id}`)
}
