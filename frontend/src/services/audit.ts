import { api } from './api'
import type { AuditEvent } from '../types/domain'

export async function fetchAuditTrail(ordenId: string): Promise<AuditEvent[]> {
  const res = await api.get<AuditEvent[]>(`/audit/${ordenId}`)
  return res.data
}

export async function downloadAuditExcel(ordenId: string): Promise<void> {
  const res = await api.get(`/audit/${ordenId}/export/excel`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `audit_${ordenId}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}
