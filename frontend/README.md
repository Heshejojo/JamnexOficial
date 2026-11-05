# Frontend - Vue 3

Este directorio contiene el panel web administrativo de JamnexCFE. La
arquitectura y el flujo de datos se explican en
[`../docs/architecture.md`](../docs/architecture.md).

## Responsabilidades

- Autenticar usuarios mediante JWT.
- Mostrar métricas del dashboard.
- Administrar dispositivos, SIMs, trabajadores y catálogos.
- Mostrar consumo diario y mensual.
- Mostrar alertas de reportes de SIM después de 72 horas.
- Dar de baja, reactivar o eliminar SIMs con confirmación.
- Consultar historial de dispositivos de cada SIM.
- Descargar reportes Excel.

## Vistas principales

- `src/views/DashboardView.vue`: métricas, consumo y alertas generales.
- `src/views/DispositivosView.vue`: equipos, estado, telemetría y reportes SIM.
- `src/views/SimsView.vue`: líneas, consumo, historial y estado de SIM.

## Desarrollo

```powershell
npm install
npm run dev
npm run build
```

La URL de la API se configura mediante `VITE_API_BASE_URL`.
