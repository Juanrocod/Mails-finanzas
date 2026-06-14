export type EstadoMinuta = 'BORRADOR' | 'APROBADO' | 'ENVIADO' | 'CONFIRMADO' | 'ALERTA'
export type TipoOperacion = 'COMPRA' | 'VENTA'
export type Liquidacion = 'CI' | '24HS' | '48HS'
export type AccionAudit = 'CREADA' | 'EDITADA' | 'APROBADA' | 'ENVIADA' | 'CONFIRMADA' | 'ALERTA_GENERADA'

export interface Orden {
  id: string
  excel_upload_id: string
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
  dj_tipo: string | null
  estado: EstadoMinuta
  texto_minuta: string
  texto_editado: boolean
  created_at: string
  updated_at: string
}

export interface AuditEvent {
  id: string
  orden_id: string
  usuario_id: string | null
  accion: AccionAudit
  ip_origen: string | null
  timestamp: string
  detalle: Record<string, unknown> | null
}

export interface DashboardPage {
  items: Orden[]
  total: number
  page: number
  size: number
}

export interface UploadResponse {
  upload_id: string
  nombre_archivo: string
  total_ordenes: number
  ordenes_validas: number
  ordenes_con_error: number
  errors: { fila: number; mensaje: string }[]
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
