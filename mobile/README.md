# Mobile - Flutter y Android

Este directorio contiene el agente Android de JamnexCFE. Flutter proporciona
la interfaz y la cola de eventos; Kotlin integra las APIs nativas necesarias
para SIMs, consumo y ejecución en segundo plano.

## Responsabilidades

- Identificar el equipo mediante Android ID.
- Leer batería, RAM, almacenamiento y conexión.
- Detectar SIMs, ICCID, operador y ranura.
- Consultar datos móviles con `NetworkStatsManager`.
- Enviar registros al backend con una credencial de dispositivo.
- Guardar eventos pendientes cuando falla una petición.
- Sincronizar al abrir, al recuperar conectividad y aproximadamente cada dos
  horas.

## Archivos principales

- `lib/main.dart`: ciclo de captura y envío desde Flutter.
- `lib/services/api_service.dart`: cliente HTTP y token local.
- `lib/services/device_service.dart`: construcción de `DeviceSnapshot`.
- `lib/providers/sync_provider.dart`: persistencia y reintento de eventos.
- `android/.../MainActivity.kt`: canal Flutter, permisos y trabajo periódico.
- `android/.../JamnexApplication.kt`: observación de conectividad.
- `android/.../JamnexSyncWorker.kt`: envío en segundo plano.

## Desarrollo y compilación

```powershell
flutter pub get
flutter analyze
flutter run
flutter build apk --debug
```

La URL se puede configurar con:

```powershell
flutter build apk --dart-define=API_BASE_URL=https://api.example.com/api
```

Consulta [`../docs/operations.md`](../docs/operations.md) para permisos,
diagnóstico de WorkManager e instalación en un dispositivo.
