# Frontend Spec — Sistema de Gestión de Órdenes Bursátiles

**Versión:** 1.0
**Fecha:** 2026-06-13
**Stack:** React 18 + TypeScript + Vite + shadcn/ui + TanStack Query + React Router v6

---

## Estructura de rutas

| Ruta | Componente | Descripción |
|------|-----------|-------------|
| `/login` | `LoginPage` | Formulario usuario + contraseña |
| `/login/2fa` | `TwoFactorPage` | Ingreso del código TOTP |
| `/dashboard/borradores` | `DashboardPage` | Lista de Minutas en BORRADOR |
| `/dashboard/aprobados` | `DashboardPage` | Lista de Minutas en APROBADO |
| `/dashboard/enviados` | `DashboardPage` | Lista de Minutas en ENVIADO |
| `/dashboard/confirmados` | `DashboardPage` | Lista de Minutas en CONFIRMADO |
| `/dashboard/alertas` | `DashboardPage` | Lista de Minutas en ALERTA |
| `/dashboard/audit` | `AuditPage` | Exportación global del Audit Trail |
| `/` | redirect | Redirige a `/dashboard/borradores` si autenticado, sino `/login` |

---

## Layout

```
┌─────────────────────────────────────────────────────────┐
│  SIDEBAR (fija, 240px)     │  CONTENIDO PRINCIPAL        │
│                            │                             │
│  [Logo / Nombre sistema]   │  [Header: título solapa +   │
│                            │   badge con contador]        │
│  ● Borradores  [badge N]   │                             │
│  ○ Aprobados   [badge N]   │  [Lista de MinutaCards]     │
│  ○ Enviados    [badge N]   │                             │
│  ○ Confirmados             │                             │
│  ○ Alertas     [badge N]   │                             │
│  ─────────────────────     │                             │
│  ○ Audit Trail             │                             │
│                            │                             │
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
- Badge de estado (BORRADOR / APROBADO / ENVIADO / CONFIRMADO / ALERTA)
- Indicador visual si tiene DJ incluida
- Indicador visual si el texto fue editado manualmente

Al hacer click → abre el `MinutaDrawer`.

**Caso especial ALERTA:** card con borde rojo y badge rojo. Muestra tiempo transcurrido desde el envío.

---

### `MinutaDrawer`
Panel lateral que se abre desde la derecha (ancho ~600px). Contenido:

**Header del drawer:**
- Nombre del cliente + cuenta comitente + cuenta cotapartista
- Badge de estado actual

**Sección: Texto de la Minuta**
- Textarea editable (solo en estado BORRADOR)
- En otros estados: texto en modo lectura + botón "Copiar al portapapeles"
- Badge "Editado manualmente" si `texto_editado = true`

**Sección: DJ (si aplica)**
- Muestra tipo de DJ incluida
- Texto completo del template aplicado (colapsable)

**Sección: Acciones**
Según el estado actual:
| Estado | Acciones disponibles |
|--------|---------------------|
| BORRADOR | [Aprobar] [Guardar edición] |
| APROBADO | [Marcar como Enviada] [Copiar texto] |
| ENVIADO | [Registrar Confirmación] [Copiar texto] |
| ALERTA | [Registrar Confirmación] |
| CONFIRMADO | — (solo lectura) |

**Sección: Audit Trail (colapsable)**
- Lista cronológica de AuditEvents de la orden
- Cada evento: acción + usuario + timestamp + IP
- Colapsada por defecto

---

### `ExcelUploadModal`
Modal que se abre al clickear "Subir Excel" en el sidebar.

Flujo:
1. **Step 1 — Selección:** Drag & drop o selector de archivo. Solo acepta `.xlsx`.
2. **Step 2 — Preview:** Muestra resumen: N órdenes detectadas, N válidas, N con error. Lista de errores por fila si los hay.
3. **Step 3 — Confirmación:** Botón "Procesar" que dispara el POST al backend. Spinner mientras procesa.
4. **Step 4 — Resultado:** "X Minutas generadas en Borradores." Cierra modal, invalida query de borradores.

---

### `AuditPage`
Tab del sidebar. Permite:
- Filtrar por rango de fechas
- Ver tabla de eventos (orden, acción, usuario, timestamp)
- Botón "Exportar a Excel" y "Exportar a PDF" → descarga directa del endpoint del backend

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
- Al cerrar sesión: POST `/auth/logout` + limpiar tokens

---

## Estado y data fetching

```
useQuery(['minutas', estado], () => fetchMinutas(estado))
  → lista de cards por solapa

useMutation(aprobarMinuta, {
  onSuccess: () => {
    queryClient.invalidateQueries(['minutas', 'borradores'])
    queryClient.invalidateQueries(['minutas', 'aprobados'])
    cerrarDrawer()
  }
})
```

Queries por solapa: `['minutas', 'borradores']`, `['minutas', 'aprobados']`, etc.
Refetch automático al volver a enfocar la ventana (TanStack Query default).

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
│   │   └── AuditPage.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx       ← sidebar + outlet
│   │   │   └── Sidebar.tsx
│   │   ├── minutas/
│   │   │   ├── MinutaCard.tsx
│   │   │   ├── MinutaDrawer.tsx
│   │   │   └── AuditTrailSection.tsx
│   │   ├── upload/
│   │   │   └── ExcelUploadModal.tsx
│   │   └── ui/                     ← componentes shadcn/ui (auto-generados)
│   ├── services/
│   │   ├── api.ts                  ← instancia axios + interceptores
│   │   ├── auth.ts
│   │   ├── minutas.ts
│   │   ├── upload.ts
│   │   └── audit.ts
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
