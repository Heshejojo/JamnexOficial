# Arquitectura y flujo de datos

## 1. Visión general

JamnexCFE está compuesto por tres aplicaciones:

```text
Android (Flutter + Kotlin)
          │ HTTPS/JSON
          ▼
Backend Django + DRF
          │ ORM
          ▼
PostgreSQL (producción) / SQLite (local)
          ▲
          │ HTTPS/JSON + JWT
          │
Panel Vue 3
```

El móvil es un agente de captura. El backend es la fuente de verdad para
dispositivos, SIMs, consumo e historial. El frontend consulta y administra los
datos; no reemplaza los registros históricos del backend.

## 2. Capas del sistema

### Backend

- **Modelos:** representan dispositivos, SIMs, consumo, telemetría y usuarios.
- **Serializadores:** validan JSON y controlan los campos que se exponen.
- **Vistas:** contienen la lógica de cada operación HTTP.
- **Permisos:** separan autenticación JWT de autenticación propia del dispositivo.
- **Migraciones:** permiten evolucionar el esquema sin perder datos.
- **Reportes:** leen los registros históricos y generan JSON o Excel.

### Frontend

- **Vistas Vue:** `DashboardView`, `DispositivosView` y `SimsView` muestran
  información y acciones de administración.
- **Axios:** agrega la URL base y los tokens a las peticiones.
- **Estado reactivo:** recalcula filtros, totales, alertas y selección actual.
- **Actualización periódica:** dispositivos y SIMs vuelven a consultar la API
  cada 30 segundos mientras la vista está activa.

### Móvil

- **Flutter/Dart:** interfaz, captura de eventos y cola local de pendientes.
- **Kotlin:** acceso a APIs Android que Flutter no puede consultar directamente,
  ejecución en segundo plano y WorkManager.
- **SharedPreferences:** guarda el token del dispositivo y la URL configurada.

## 3. Identidad y autenticación

Hay dos flujos independientes:

### Usuario del panel

1. El usuario envía credenciales a `/api/auth/login/`.
2. Django devuelve un access token y un refresh token JWT.
3. Axios envía `Authorization: Bearer <access-token>`.
4. Cuando el access token expira, el frontend usa `/api/auth/refresh/`.
5. Los permisos de rol controlan altas, cambios, bajas y reportes.

### Dispositivo Android

1. El agente envía `device_uuid` a `/api/device/register/`.
2. El backend crea o recupera `Dispositivo`.
3. El backend devuelve una credencial propia del dispositivo.
4. Las siguientes peticiones usan `Authorization: Device <token>`.
5. Si el token deja de ser válido, el worker registra de nuevo el dispositivo y
   repite la petición una vez.

## 4. Registro de una sincronización

Una sincronización completa sigue este orden:

1. Registrar o identificar el equipo.
2. Enviar estado de batería, RAM, almacenamiento y conexión.
3. Enviar una petición `/device/sim/` por cada SIM activa.
4. Enviar `/device/sims/status/` con el número de SIMs detectadas.
5. Enviar consumo diario y, cuando existe, consumo semanal.
6. El backend responde con el resultado de cada operación.

El orden es importante: primero se conocen las SIMs y después el consumo puede
asociarse a la ranura o a la SIM correcta.

## 5. SIMs e historial

`Sim` representa una línea actual. `HistorialSim` representa una presencia de
esa línea en un dispositivo:

```text
Sim 42
 ├── HistorialSim: dispositivo A, ranura 0, desde/hasta
 └── HistorialSim: dispositivo B, ranura 1, desde/hasta
```

`register_presence` abre o actualiza el periodo actual. Si la SIM aparece en
otro dispositivo, cierra el periodo anterior. La interfaz puede compactar
movimientos consecutivos iguales para facilitar la lectura, pero nunca elimina
filas de la base de datos.

Una baja cambia `activo` a falso. Una eliminación definitiva borra la SIM y las
relaciones que dependen de ella; el consumo puede quedar conservado con
`sim = NULL` por la política de eliminación configurada en el modelo.

## 6. Consumo

`Consumo` guarda un registro por periodo y dispositivo. El registro diario es
el origen de los totales mensuales:

```text
ConsumoSyncState(dispositivo, fecha, sim)
                 │
                 ▼
Consumo(periodo=diario, dispositivo, sim, fecha)
                 │
                 ▼
Excel mensual / dashboard / vista de SIM
```

El backend calcula deltas con `ConsumoSyncState`. La restricción única incluye
la SIM para evitar que dos líneas del mismo equipo compartan el mismo contador.

La tarjeta “Datos móviles usados hoy” del frontend suma los registros diarios
de la fecha local actual. La tarjeta mensual suma todos los registros diarios
del año y mes seleccionados.

## 7. Conectividad y segundo plano

`JamnexApplication` observa la red predeterminada. Solo considera utilizable
una red con `NET_CAPABILITY_INTERNET` y, en versiones modernas, con
`NET_CAPABILITY_VALIDATED`.

Cuando la conexión pasa de no disponible a disponible:

1. Lee `base_url` de preferencias.
2. Crea un `OneTimeWorkRequest`.
3. Exige `NetworkType.CONNECTED`.
4. Reemplaza cualquier sincronización inmediata previa.

`MainActivity` mantiene un `PeriodicWorkRequest` de aproximadamente dos horas.
La política `UPDATE` permite reemplazar la tarea persistida cuando se instala
una versión con nuevas restricciones.

Android puede retrasar un trabajo por ahorro de batería, modo reposo o
restricciones del fabricante. La app debe abrirse al menos una vez después de
instalarse. Una aplicación detenida mediante “Forzar detención” no puede
recibir trabajos hasta que el usuario la abra de nuevo.

## 8. Responsabilidades por archivo principal

| Archivo | Qué hace |
|---|---|
| `mobile/lib/main.dart` | Inicializa Flutter, recopila el snapshot y envía eventos o los guarda como pendientes. |
| `mobile/lib/services/device_service.dart` | Traduce la telemetría nativa a `DeviceSnapshot`. |
| `mobile/lib/services/api_service.dart` | Realiza peticiones HTTP del agente. |
| `mobile/android/.../MainActivity.kt` | Expone el canal Flutter, permisos y programación periódica. |
| `mobile/android/.../JamnexApplication.kt` | Observa cambios de conectividad y activa sincronización inmediata. |
| `mobile/android/.../JamnexSyncWorker.kt` | Ejecuta el envío completo fuera de la interfaz. |
| `backend/dispositivos/views.py` | Registra dispositivos, SIMs, telemetría y delta de consumo. |
| `backend/sims/history.py` | Abre, actualiza y cierra presencias de SIM. |
| `backend/consumos/models.py` | Define registros de consumo y estado del contador. |
| `backend/reportes/views.py` | Construye resumen y archivos Excel. |
| `frontend/src/views/DispositivosView.vue` | Lista equipos, estados, alertas y ficha técnica. |
| `frontend/src/views/SimsView.vue` | Lista SIMs, consumo, historial y acciones de estado. |
