import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchMinutas,
  aprobarMinuta,
  marcarEnviada,
  registrarConfirmacion,
  editarTexto,
} from '../services/minutas'
import type { EstadoMinuta } from '../types/domain'

export function useMinutas(estado: EstadoMinuta) {
  return useQuery({
    queryKey: ['minutas', estado],
    queryFn: () => fetchMinutas(estado),
  })
}

export function useAprobarMinuta() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: aprobarMinuta,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['minutas', 'BORRADOR'] })
      qc.invalidateQueries({ queryKey: ['minutas', 'APROBADO'] })
    },
  })
}

export function useMarcarEnviada() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: marcarEnviada,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['minutas', 'APROBADO'] })
      qc.invalidateQueries({ queryKey: ['minutas', 'ENVIADO'] })
    },
  })
}

export function useRegistrarConfirmacion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: registrarConfirmacion,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['minutas', 'ENVIADO'] })
      qc.invalidateQueries({ queryKey: ['minutas', 'ALERTA'] })
      qc.invalidateQueries({ queryKey: ['minutas', 'CONFIRMADO'] })
    },
  })
}

export function useEditarTexto() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ ordenId, texto }: { ordenId: string; texto: string }) =>
      editarTexto(ordenId, texto),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['minutas', 'BORRADOR'] })
    },
  })
}
