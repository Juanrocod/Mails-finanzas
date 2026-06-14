import { api } from './api'
import type { UploadResponse } from '../types/domain'

export async function uploadExcel(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await api.post<UploadResponse>('/uploads/excel', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}
