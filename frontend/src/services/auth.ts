import { api } from './api'
import type { LoginResponse, TokenResponse } from '../types/domain'

let pendingToken: string | null = null

export function setPendingToken(token: string): void {
  pendingToken = token
}

export function getPendingToken(): string | null {
  return pendingToken
}

export function clearPendingToken(): void {
  pendingToken = null
}

export async function login(
  username: string,
  password: string
): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>('/auth/login', { username, password })
  return res.data
}

export async function verifyTotp(
  pending_token: string,
  code: string
): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>('/auth/verify-totp', {
    pending_token,
    code,
  })
  return res.data
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}
