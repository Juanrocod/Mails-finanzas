# Frontend Spec — Sistema de Gestión de Órdenes Bursátiles (MVP)

**Versión:** 2.0 (MVP sin persistencia — ver ADR-0006)
**Fecha:** 2026-06-14
**Stack:** React 18 + TypeScript + Vite + shadcn/ui + TanStack Query + React Router v6

---

## Estructura de rutas

| Ruta | Componente | Descripción |
|------|-----------|-------------|
| `/login` | `LoginPage` | Formulario usuario + contraseña |
| `/login/2fa` | `TwoFactorPage` | Ingreso del código TOTP |
| `/dashboard/borradores` | `DashboardPage` | Lista de Minutas en BORRADOR |
| `/dashboard/enviados` | `DashboardPage` | Lista de Minutas en ENVIADO |
| `/dashboard/plantilla` | `PlantillaPage` | Editor de plantilla estándar de mail |
| `/dashboard/config-dj` | `ConfigDJPage` | Toggle y texto de alerta para DJ |
| `/` | redirect | Redirige a `/dashboard/borradores` si autenticado, sino `/login` |

> Rutas eliminadas respecto al spec original: `/dashboard/aprobados`, `/dashboard/confirmados`, `/dashboard/alertas`, `/dashboard/audit`.

---

## Layout

```
┌─────────────────────────────────────────────────────────┐
│  SIDEBAR (fija, 240px)     │  CONTENIDO PRINCIPAL        │
│                            │                             │
│  [Logo / Nombre sistema]   │  [Header: título solapa +   │
│                            │   badge con contador]        │
│  ● Borradores  [badge N]   │                             │
│  ○ Enviados    [badge N]   │  [Lista de MinutaCards]     │
│  ─────────────────────     │                             │
│  ○ Plantilla Estándar      │                             │
│  ○ Config DJ               │                             │
│  ─────────────────────     │                             │
│  [Subir Excel]  ← botón    │                             │
│  ─────────────────────     │                             │
│  [Avatar] Middle Office    │                             │
│  [Cerrar sesión]           │                             │
└─────────────────────────────────────────────────────────┘
```

---

## Componentes principales

### `MinutaCard`
Card en la lista del Dashboard. Muestra:
- Nombre del cliente
- Instrumento + tipo (Compra / Venta) — con badge de color (verde/rojo)
- Cantidad × Precio (Moneda)
- Condición de liquidación (CI / 24HS / 48HS)
- Fecha y hora de la operación
- Badge de estado (BORRADOR / ENVIADO)
- Indicador visual si tiene DJ incluida
- Indicador visual si el texto fue editado manualmente

Al hacer click → abre el `MinutaDrawer`.

---

### `MinutaDrawer`
Panel lateral que se abre desde la derecha (ancho ~600px). Contenido:

**Header del drawer:**
- Nombre del cliente + cuenta comitente + cuenta cotapartista
- Badge de estado actual

**Sección: Texto de la Minuta**
- Textarea editable (solo en estado BORRADOR)
- En estado ENVIADO: texto en modo lectura
- Botón "Copiar contenido" (Clipboard API nativa) — visible siempre
- Badge "Editado manualmente" si `texto_editado = true`

**Sección: DJ (si aplica)**
- Muestra indicador de DJ incluida con ícono triángulo ⚠
- Texto completo del alerta (colapsable)

**Sección: Acciones**
Según el estado actual:

| Estado | Acciones disponibles |
|--------|---------------------|
| BORRADOR | [Guardar edición] [Copiar contenido] [Enviado] |
| ENVIADO | [Copiar contenido] |

> "Enviado" marca la minuta como ENVIADO y la mueve al tab Enviados.  
> No hay botón "Aprobar": el flujo es editar → copiar → marcar enviado.

---

### `ExcelUploadModal`
Modal que se abre al clickear "Subir Excel" en el sidebar.

Flujo:
1. **Step 1 — Selección:** Drag & drop o selector de archivo. Solo acepta `.xlsx`.
2. **Step 2 — Preview:** Muestra resumen: N órdenes detectadas, N válidas, N con error. Lista de errores por fila si los hay.
3. **Step 3 — Confirmación:** Botón "Procesar" que dispara el POST al backend. Spinner mientras procesa.
4. **Step 4 — Resultado:** "X Minutas generadas en Borradores." Cierra modal, invalida query de borradores.

---

### `PlantillaPage`
Tab del sidebar. Editor de texto (Textarea grande) con la plantilla estándar de mail.
- Carga el texto con `GET /plantilla`
- Botón "Guardar" → `PATCH /plantilla`
- Cambios afectan minutas de la sesión actual (en RAM)

---

### `ConfigDJPage`
Tab del sidebar. Configuración de Declaración Jurada:
- Toggle "DJ activa" (Switch shadcn/ui)
- Textarea "Texto de alerta" — el texto que aparece con ⚠ en la minuta cuando la DJ está activa
- Botón "Guardar" → `PATCH /config/dj`
- Carga con `GET /config/dj`

---

## Flujo de autenticación

```
/login → [usuario + contraseña] → POST /auth/login
  → si pending_2fa → /login/2fa → [código TOTP] → POST /auth/verify-2fa
  → guarda access_token + refresh_token en memoria (no localStorage)
  → redirect /dashboard/borradores
```

**Manejo de tokens:**
- `access_token` en memoria (variable de módulo en el cliente Axios)
- `refresh_token` en httpOnly cookie (si el backend lo soporta) o en memoria
- Interceptor Axios: si recibe 401 → intenta refresh → si falla → redirect a `/login`
- Al cerrar sesión: POST `/auth/logout` + limpiar tokens + las minutas en RAM desaparecen

---

## Estado y data fetching

```ts
// Minutas por estado
useQuery(['minutas', estado], () => fetchMinutas(estado))

// Marcar como enviado
useMutation(marcarEnviado, {
  onSuccess: () => {
    queryClient.invalidateQueries(['minutas', 'BORRADOR'])
    queryClient.invalidateQueries(['minutas', 'ENVIADO'])
    cerrarDrawer()
  }
})

// Plantilla
useQuery(['plantilla'], fetchPlantilla)
useMutation(guardarPlantilla)

// Config DJ
useQuery(['config-dj'], fetchConfigDJ)
useMutation(guardarConfigDJ)
```

Query keys: `['minutas', 'BORRADOR']`, `['minutas', 'ENVIADO']`, `['plantilla']`, `['config-dj']`.

---

## Dependencias npm

```json
{
  "react": "^18",
  "react-dom": "^18",
  "react-router-dom": "^6",
  "@tanstack/react-query": "^5",
  "axios": "^1",
  "react-hook-form": "^7",
  "date-fns": "^3",
  "lucide-react": "latest",
  "tailwindcss": "^3",
  "class-variance-authority": "latest",
  "clsx": "latest",
  "tailwind-merge": "latest"
}
```

shadcn/ui se instala via CLI (`npx shadcn@latest init`), no como dependencia directa.

---

## Variables de entorno

```
VITE_API_URL=http://localhost:8000
```

---

## Estructura de carpetas

```
frontend/
├── src/
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── TwoFactorPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── PlantillaPage.tsx
│   │   └── ConfigDJPage.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx       ← sidebar + outlet
│   │   │   └── Sidebar.tsx
│   │   ├── minutas/
│   │   │   ├── MinutaCard.tsx
│   │   │   └── MinutaDrawer.tsx
│   │   ├── upload/
│   │   │   └── ExcelUploadModal.tsx
│   │   └── ui/                     ← componentes shadcn/ui (auto-generados)
│   ├── services/
│   │   ├── api.ts                  ← instancia axios + interceptores
│   │   ├── auth.ts
│   │   ├── minutas.ts
│   │   ├── upload.ts
│   │   ├── plantilla.ts
│   │   └── configDJ.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   └── useMinutas.ts
│   ├── types/
│   │   └── domain.ts               ← tipos TypeScript del dominio
│   └── main.tsx
├── .env
├── package.json
└── vite.config.ts
```

> Eliminados respecto al spec original: `AuditPage.tsx`, `AuditTrailSection.tsx`, `audit.ts`.
