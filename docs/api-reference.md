# Referencia de la API

La API se publica bajo `/api/`. Las rutas administrativas usan JWT; las rutas
que comienzan con `/device/` usan la credencial propia del dispositivo.

## Autenticación de usuarios

| Método | Ruta | Uso |
|---|---|---|
| POST | `/api/auth/login/` | Obtiene access y refresh JWT. |
| POST | `/api/auth/refresh/` | Renueva el access token. |
| POST | `/api/auth/logout/` | Cierra la sesión según la implementación vigente. |
| GET | `/api/usuarios/me/` | Consulta el usuario autenticado. |
| GET/POST | `/api/usuarios/` | Administra usuarios. |
| GET/POST | `/api/roles/` | Administra roles. |

Encabezado:

```http
Authorization: Bearer <access-token>
Content-Type: application/json
```

## Rutas del dispositivo Android

Todas estas rutas usan:

```http
Authorization: Device <device-token>
Content-Type: application/json
```

### Registrar equipo

`POST /api/device/register/`

```json
{
  "device_uuid": "android-id",
  "fabricante": "Lenovo",
  "modelo": "LenovoTB-7104I",
  "version_android": "8.1.0",
  "android_sdk": 27,
  "ram_total": 2048,
  "almacenamiento_total": 16000
}
```

Devuelve la credencial del dispositivo. El agente la guarda localmente y la
reutiliza en las siguientes peticiones.

### Estado técnico

`POST /api/device/status/`

Recibe batería, RAM, almacenamiento, conexión, temperatura y timestamp. Crea
un registro de telemetría y actualiza `ultimo_contacto` del dispositivo.

### Tipo de red

`POST /api/device/network/`

```json
{ "tipo_conexion": "WIFI" }
```

Valores válidos: `WIFI`, `DATOS_MOVILES` y `SIN_CONEXION`.

### SIM detectada

`POST /api/device/sim/`

Recibe `sim_uuid`, ICCID, ranura, operador, país, número, eSIM, tecnología y
roaming. La vista identifica la SIM, actualiza su dispositivo y registra la
presencia histórica.

### Cantidad de SIMs

`POST /api/device/sims/status/`

```json
{ "sim_count": 2 }
```

Actualiza `sim_count_reported` y `sims_reported_at`. Un reporte de cero SIMs
solo se muestra como alerta después de 72 horas sin un reporte posterior.

### Consumo

`POST /api/device/consumption/`

```json
{
  "consumo_datos_movil": 0.08,
  "periodo": "diario",
  "sim_slot": 0
}
```

`periodo` puede ser `diario`, `semanal`, `mensual` o `personalizado`. Para el
periodo diario, el backend calcula el delta utilizando
`dispositivo + fecha + sim`. `sim_slot` permite asociar el reporte a la línea
de datos activa.

### Revocar credencial

`POST /api/dispositivos/<id>/revoke/`

Ruta administrativa para invalidar la credencial de un dispositivo.

## Catálogos y registros administrativos

| Recurso | Rutas |
|---|---|
| Áreas | `GET/POST /api/areas/`, `GET/PUT/DELETE /api/areas/<id>/` |
| Trabajadores | `GET/POST /api/trabajadores/`, `GET/PUT/DELETE /api/trabajadores/<id>/` |
| Dispositivos | `GET/POST /api/dispositivos/`, `GET/PUT/PATCH/DELETE /api/dispositivos/<id>/` |
| SIMs | `GET/POST /api/sims/`, `GET/PUT/PATCH/DELETE /api/sims/<id>/` |
| Consumos | `GET /api/consumos/`, `GET /api/consumos/<id>/` |
| Redes | `GET /api/redes/`, `GET /api/redes/<id>/` |
| Batería | `GET/POST /api/bateria/`, `GET/PUT/DELETE /api/bateria/<id>/` |
| RAM | `GET/POST /api/ram/`, `GET/PUT/DELETE /api/ram/<id>/` |
| Almacenamiento | `GET/POST /api/almacenamiento/`, `GET/PUT/DELETE /api/almacenamiento/<id>/` |

## Operaciones de SIM

| Método | Ruta | Uso |
|---|---|---|
| POST | `/api/sims/<id>/status/` | Baja reversible o reactivación con `{ "activo": true/false }`. |
| GET | `/api/sims/<id>/historial/` | Historial de dispositivos y ranuras. |
| GET | `/api/sims/movimientos/` | Movimientos recientes. |
| GET | `/api/sims/conflicts/` | Conflictos de transferencia. |
| POST | `/api/sims/conflicts/<id>/<action>/` | `transfer`, `dismiss` o `acknowledge`. |
| GET/POST | `/api/asignaciones-sim/` | Asignaciones administrativas. |

## Dashboard y reportes

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/dashboard/summary/?anio=2026&mes=10` | Métricas y consumo del periodo. |
| GET | `/api/reportes/sims/<id>/exportar/?anio=2026&mes=10&formato=xlsx` | Excel mensual de una SIM. |
| GET | `/api/reportes/dispositivos/exportar/?anio=2026&mes=10&formato=xlsx` | Excel mensual de dispositivos. |

El Excel de SIM incluye resumen mensual, detalle diario y acumulado
progresivo. Un reporte anual se obtiene seleccionando cada mes del año; el
endpoint vigente es mensual.
