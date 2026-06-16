import { api } from './api'
import type { UploadMVPResponse } from '../types/domain'

export async function uploadExcel(file: File): Promise<UploadMVPResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await api.post<UploadMVPResponse>('/uploads/excel', formData)
  return res.data
}
