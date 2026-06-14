---
paths:
  - "frontend/**/*.tsx"
  - "frontend/**/*.ts"
  - "frontend/components/**"
---

## Stack

- React 18 + TypeScript + Vite
- shadcn/ui (componentes en `src/components/ui/`) + Tailwind CSS v3
- TanStack Query v5 para estado del servidor
- React Router v6
- React Hook Form v7
- Axios v1 con interceptores en `src/services/api.ts`
- date-fns v3 para formateo de fechas (locale `es`)
- lucide-react para iconos

## Estructura de carpetas

```
src/
├── pages/          ← LoginPage, TwoFactorPage, DashboardPage, AuditPage
├── components/
│   ├── layout/     ← AppLayout.tsx, Sidebar.tsx
│   ├── minutas/    ← MinutaCard.tsx, MinutaDrawer.tsx, AuditTrailSection.tsx
│   ├── upload/     ← ExcelUploadModal.tsx
│   └── ui/         ← shadcn/ui (auto-generados, no editar a mano)
├── services/       ← api.ts, auth.ts, minutas.ts, upload.ts, audit.ts
├── hooks/          ← useAuth.ts, useMinutas.ts
└── types/          ← domain.ts (todos los tipos del dominio)
```

## Naming

- Componentes: PascalCase (`MinutaCard`, `ExcelUploadModal`)
- Hooks: camelCase con prefijo `use` (`useMinutas`, `useAuth`)
- Servicios: camelCase (`fetchMinutas`, `aprobarMinuta`)
- Query keys: arrays `['minutas', estado]` donde `estado` es el enum de estado
- Archivos: nombre igual al export default (`MinutaCard.tsx` exporta `MinutaCard`)

## Rutas

```
/login                    → LoginPage
/login/2fa                → TwoFactorPage
/dashboard/borradores     → DashboardPage (estado=BORRADOR)
/dashboard/aprobados      → DashboardPage (estado=APROBADO)
/dashboard/enviados       → DashboardPage (estado=ENVIADO)
/dashboard/confirmados    → DashboardPage (estado=CONFIRMADO)
/dashboard/alertas        → DashboardPage (estado=ALERTA)
/dashboard/audit          → AuditPage
/                         → redirect a /dashboard/borradores si auth, sino /login
```

Rutas del Dashboard envueltas en un guard que verifica token. Si no hay token → redirect `/login`.

## Tipos de dominio (`src/types/domain.ts`)

```ts
type EstadoMinuta = 'BORRADOR' | 'APROBADO' | 'ENVIADO' | 'CONFIRMADO' | 'ALERTA'
type TipoOperacion = 'COMPRA' | 'VENTA'
type Liquidacion = 'CI' | '24HS' | '48HS'

interface Orden {
  id: string
  cliente_nombre: string
  instrumento: string
  tipo: TipoOperacion
  cantidad: number
  precio: number
  moneda: string
  liquidacion: Liquidacion
  fecha_operacion: string  // ISO 8601
  dj_aplicada: boolean
  dj_tipo: string | null
  estado: EstadoMinuta
  texto_minuta: string
  texto_editado: boolean
  creado_en: string
}

interface AuditEvent {
  id: string
  orden_id: string
  usuario_id: string
  accion: 'CREADA' | 'EDITADA' | 'APROBADA' | 'ENVIADA' | 'CONFIRMADA' | 'ALERTA_GENERADA'
  ip_origen: string
  timestamp: string
  detalle: Record<string, unknown> | null
}
```

## Estado del servidor — TanStack Query

Query por solapa:
```ts
useQuery({ queryKey: ['minutas', estado], queryFn: () => fetchMinutas(estado) })
```

Tras cada mutación, invalidar las queries afectadas:
```ts
useMutation({
  mutationFn: aprobarMinuta,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['minutas', 'BORRADOR'] })
    queryClient.invalidateQueries({ queryKey: ['minutas', 'APROBADO'] })
  }
})
```

No usar `useState` para datos que vienen del servidor. Solo `useState` para estado de UI (drawer abierto/cerrado, paso del modal de upload).

## Axios (`src/services/api.ts`)

- Instancia única con `baseURL = import.meta.env.VITE_API_URL`
- Interceptor de request: añade `Authorization: Bearer <token>` desde variable en módulo (no localStorage)
- Interceptor de response: si 401 → intenta refresh token → si falla → redirect `/login` y limpia tokens

## Autenticación

- `access_token` almacenado en variable de módulo en `src/services/api.ts` (no en localStorage ni sessionStorage)
- Flujo login: POST `/auth/login` → si `pending_2fa: true` → redirect `/login/2fa` → POST `/auth/verify-2fa` → guardar token → redirect `/dashboard/borradores`
- Logout: POST `/auth/logout` + limpiar variable de token + redirect `/login`

## Layout

- Sidebar fija de 240px a la izquierda, contenido principal ocupa el resto
- Sidebar muestra badge con contador en: Borradores, Aprobados, Enviados, Alertas
- Botón "Subir Excel" en la parte inferior del sidebar, sobre el avatar/logout
- `AppLayout.tsx` usa `<Outlet />` de React Router para el contenido

## MinutaCard

Campos visibles en la card:
- Nombre del cliente
- Instrumento + badge de tipo (COMPRA=verde, VENTA=rojo)
- `cantidad × precio moneda` (ej: `100 × $1.250,00 ARS`)
- Condición de liquidación
- Fecha y hora de operación (formato `dd/MM/yyyy HH:mm`)
- Badge de estado
- Ícono DJ si `dj_aplicada = true`
- Ícono lápiz si `texto_editado = true`

Card ALERTA: borde rojo (`border-red-500`), muestra tiempo transcurrido desde `creado_en`.

Click en card → abre `MinutaDrawer`.

## MinutaDrawer

- Ancho 600px, se abre desde la derecha
- Header: nombre cliente + cuentas + badge estado
- Textarea editable solo cuando `estado === 'BORRADOR'`; en otros estados modo lectura
- Botón "Copiar al portapapeles" (Clipboard API nativa) en estados APROBADO, ENVIADO, ALERTA, CONFIRMADO
- Badge "Editado manualmente" visible si `texto_editado = true`
- Sección DJ colapsable si `dj_aplicada = true`
- Acciones según estado:
  - BORRADOR → [Guardar edición] [Aprobar]
  - APROBADO → [Copiar texto] [Marcar como Enviada]
  - ENVIADO → [Copiar texto] [Registrar Confirmación]
  - ALERTA → [Registrar Confirmación]
  - CONFIRMADO → sin acciones
- Sección Audit Trail colapsable al final, colapsada por defecto

## ExcelUploadModal

4 pasos con estado local (`useState`):
1. Selección de archivo (drag & drop + input `accept=".xlsx"`)
2. Preview: N órdenes, N válidas, N errores. Lista de errores por fila.
3. Spinner durante POST a `/uploads/`
4. Resultado: "X Minutas generadas." → cerrar modal → `invalidateQueries(['minutas', 'BORRADOR'])`

## Formateo de fechas

```ts
import { format } from 'date-fns'
import { es } from 'date-fns/locale'

format(new Date(fecha_operacion), 'dd/MM/yyyy HH:mm', { locale: es })
```

## Variable de entorno

`VITE_API_URL` en `frontend/.env` (no commitear). Valor de desarrollo: `http://localhost:8000`.
