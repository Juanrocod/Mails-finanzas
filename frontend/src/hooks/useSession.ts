// frontend/src/hooks/useSession.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchPlantilla, guardarPlantilla } from '../services/plantilla'
import { fetchAllConfigDJ, crearConfigDJ, actualizarConfigDJ, eliminarConfigDJ } from '../services/configDJ'
import { getConfigFiltros, patchConfigFiltros } from '../services/configFiltros'
import { agregarFiltrada, agregarTodasFiltradas } from '../services/minutas'
import type { ConfigDJ, ConfigFiltros } from '../types/domain'

export function usePlantilla() {
  return useQuery({
    queryKey: ['plantilla'],
    queryFn: fetchPlantilla,
  })
}

export function useGuardarPlantilla() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (texto: string) => guardarPlantilla(texto),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plantilla'] })
    },
  })
}

export function useConfigDJList() {
  return useQuery({
    queryKey: ['config-dj'],
    queryFn: fetchAllConfigDJ,
  })
}

export function useCrearConfigDJ() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (config: ConfigDJ) => crearConfigDJ(config),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config-dj'] })
    },
  })
}

export function useActualizarConfigDJ() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, config }: { id: number; config: ConfigDJ }) => actualizarConfigDJ(id, config),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config-dj'] })
    },
  })
}

export function useEliminarConfigDJ() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => eliminarConfigDJ(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config-dj'] })
    },
  })
}

export function useConfigFiltros() {
  return useQuery({
    queryKey: ['config', 'filtros-minutas'],
    queryFn: getConfigFiltros,
  })
}

export function usePatchConfigFiltros() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (config: ConfigFiltros) => patchConfigFiltros(config),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config', 'filtros-minutas'] })
    },
  })
}

export function useAgregarFiltrada() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (minutaId: string) => agregarFiltrada(minutaId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['minutas'] })
    },
  })
}

export function useAgregarTodasFiltradas() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: agregarTodasFiltradas,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['minutas'] })
    },
  })
}
