// frontend/src/services/configDJ.ts
import { api } from './api'
import type { ConfigDJ } from '../types/domain'

export async function fetchConfigDJ(): Promise<ConfigDJ> {
  const res = await api.get<ConfigDJ>('/config/dj')
  return res.data
}

export async function guardarConfigDJ(config: ConfigDJ): Promise<ConfigDJ> {
  const res = await api.patch<ConfigDJ>('/config/dj', config)
  return res.data
}
