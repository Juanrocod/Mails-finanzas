// frontend/src/types/domain.ts
export type EstadoMinuta = 'BORRADOR' | 'ENVIADO'
export type TipoOperacion = 'COMPRA' | 'VENTA'
export type Liquidacion = 'CI' | '24HS' | '48HS'

export interface Minuta {
  id: string
  cliente_nombre: string
  cliente_email: string
  cuenta_comitente: string
  cuenta_cotapartista: string
  instrumento: string
  tipo: TipoOperacion
  cantidad: number
  precio: number
  moneda: string
  liquidacion: Liquidacion
  fecha_operacion: string
  dj_aplicada: boolean
  dj_texto: string | null
  estado: EstadoMinuta
  texto_minuta: string
  texto_editado: boolean
  creado_en: string
}

export interface SessionMinutasResponse {
  items: Minuta[]
  total: number
}

export interface ConfigDJ {
  activa: boolean
  texto_alerta: string
}

export interface Plantilla {
  texto: string
}

export interface UploadResponse {
  nombre_archivo: string
  total_ordenes: number
  ordenes_validas: number
  ordenes_con_error: number
  errors: { fila: number; mensaje: string }[]
  minutas: Minuta[]
}

export interface LoginResponse {
  pending_token: string
  message: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}
