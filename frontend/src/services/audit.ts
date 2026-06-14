import { api } from './api'
import type { AuditEvent } from '../types/domain'

export async function fetchAuditTrail(ordenId: string): Promise<AuditEvent[]> {
  const res = await api.get<AuditEvent[]>(`/audit/${ordenId}`)
  return res.data
}

export function getAuditExcelUrl(ordenId: string): string {
  return `${import.meta.env.VITE_API_URL}/audit/${ordenId}/export/excel`
}
