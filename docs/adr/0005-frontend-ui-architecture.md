# ADR-0005: Arquitectura de UI del Frontend

## Estado
Aceptado

## Contexto
El frontend es una SPA de uso interno (Middle Office) orientada a datos: listas de minutas, acciones sobre ellas, y un audit trail exportable. El único usuario es Middle Office en escritorio. Se evaluaron distintas librerías de componentes y patrones de navegación y estado.

## Decisiones

### Librería de componentes: shadcn/ui + Tailwind CSS
Se evaluaron Ant Design, Material UI y shadcn/ui.
- Ant Design tiene componentes financieros ricos pero su tema corporativo es difícil de customizar y arrastra peso visual innecesario para una app interna.
- Material UI es madura pero impone el lenguaje visual de Google, difícil de quitar.
- shadcn/ui (Radix UI primitives + Tailwind) ofrece control total sobre el estilo, componentes accesibles out-of-the-box, y se integra naturalmente con Vite + TypeScript sin theming pesado.

### Layout: sidebar vertical fija
El Dashboard tiene 5 solapas (Borradores, Aprobados, Enviados, Confirmados, Alertas). Un sidebar vertical maximiza el espacio vertical disponible para las listas de minutas y provee lugar natural para el botón "Subir Excel" y el logout en la parte inferior.

### Detalle de Minuta: drawer lateral
El flujo de Middle Office es revisión en lote: ver minuta → aprobar → siguiente. Un drawer que se abre desde la derecha sobre la lista permite ese ciclo sin cambiar de página. Al completar la acción principal (aprobar, marcar enviada), el drawer se cierra y la lista se actualiza en lugar. Alternativa descartada: página separada con URL propia — añade fricción innecesaria para el flujo repetitivo.

### Estado del servidor: TanStack Query
Las acciones del Dashboard (aprobar, marcar enviada, confirmar) deben invalidar las queries correspondientes para mantener las listas sincronizadas sin recargar la página. TanStack Query provee ese mecanismo (invalidateQueries) con cache, retry y loading states built-in. La gestión manual con useState/useEffect requeriría construir ese mismo mecanismo a mano.

### Audit Trail: sección colapsable en el drawer
El historial de eventos de cada Orden vive en la parte inferior del drawer de detalle, colapsable. Middle Office puede verlo sin salir del contexto de la minuta. La exportación global del Audit Trail (PDF/Excel) es una tab separada en el sidebar.

## Consecuencias
- **Positivo:** shadcn/ui permite customizar el diseño sin luchar contra un tema impuesto.
- **Positivo:** El drawer mantiene el contexto de lista durante la revisión en lote.
- **Positivo:** TanStack Query elimina la sincronización manual de estado tras cada acción.
- **Neutro:** shadcn/ui requiere copiar los componentes al repo (no es una dependencia npm clásica) — esto es intencional y da control sobre versiones.
- **Negativo:** Si en Fase 2 se agregan roles (Admin, Compliance), el sidebar deberá adaptarse para mostrar items según permisos.
