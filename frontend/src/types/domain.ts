export type EstadoMinuta = "BORRADOR" | "ENVIADO" | "FILTRADA";

export interface Minuta {
  id: string;
  // Campos del Excel
  cliente_nombre: string;
  cuenta_comitente: string;
  cuenta_cotapartista: string;
  id_orden: number;
  fecha_operacion: string; // ISO datetime string
  fecha_liquidacion: string;
  operacion: string;
  instrumento: string;
  moneda: string;
  cantidad: number;       // -1 = N/A
  precio: number;         // -1 = N/A
  monto: number;
  estado_orden: string;
  cantidad_operada: number; // -1 = N/A
  precio_operado: number;   // -1 = N/A
  operador: string;
  origen: string;
  asesor: string;
  requiere_conformidad: number; // 0 | 1
  // Campos de sesión
  dj_aplicada: boolean;
  dj_texto: string | null;
  estado: EstadoMinuta;
  filtro_motivo: string | null;
  texto_minuta: string;
  texto_editado: boolean;
  creado_en: string; // ISO datetime string
}

export interface RowError {
  fila: number;
  mensaje: string;
}

export interface UploadMVPResponse {
  ordenes_validas: number;
  ordenes_con_error: number;
  ordenes_filtradas: number;
  errors: RowError[];
  minutas: Minuta[];
}

export type CampoRegla =
  | "operacion"
  | "operador"
  | "origen"
  | "estado"
  | "moneda"
  | "instrumento"
  | "cantidad"
  | "precio"
  | "monto"
  | "cantidad_operada"
  | "precio_operado"
  | "requiere_conformidad";

export type OperadorRegla = "=" | "!=" | ">" | "<" | ">=" | "<=";

export interface ReglaConfig {
  campo: CampoRegla;
  operador: OperadorRegla;
  valor: string;
}

export interface ConfigDJ {
  id?: number;
  nombre: string;
  activa: boolean;
  incluir_texto_en_minuta: boolean;
  texto_alerta: string;
  reglas: ReglaConfig[];
  logica: "AND" | "OR";
  activar_si_requiere_conformidad: boolean;
}

export interface ConfigFiltros {
  reglas: ReglaConfig[];
  logica: "AND" | "OR";
}

export interface SessionMinutasResponse {
  items: Minuta[];
  total: number;
}

export interface PlantillaResponse {
  texto: string;
}
