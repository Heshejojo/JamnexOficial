# Mobile - Flutter y Android

Este directorio contiene el agente Android de JamnexCFE. Flutter proporciona
la interfaz y la cola de eventos; Kotlin integra las APIs nativas necesarias
para SIMs, consumo y ejecución en segundo plano.

## Responsabilidades

- Identificar el equipo mediante Android ID.
- Leer batería, RAM, almacenamiento y conexión.
- Detectar SIMs, ICCID, operador y ranura.
- Solicitar permisos de teléfono y número de línea cuando sean necesarios.
- Consultar datos móviles con `NetworkStatsManager`.
- Enviar registros al backend con una credencial de dispositivo.
- Guardar eventos pendientes cuando falla una petición.
- Sincronizar al abrir, al recuperar Wi-Fi o datos móviles y aproximadamente
  cada dos horas.
- Solicitar una ruta celular para la API y usar Wi-Fi como respaldo cuando la
  conexión celular no esté disponible o falle.

## Archivos principales

- `lib/main.dart`: ciclo de captura y envío desde Flutter.
- `lib/services/api_service.dart`: cliente HTTP y token local.
- `lib/services/device_service.dart`: construcción de `DeviceSnapshot`.
- `lib/providers/sync_provider.dart`: persistencia y reintento de eventos.
- `android/.../ApiNetworkClient.kt`: selección de red celular/Wi-Fi y POSTs
  asociados a la red elegida.
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

La URL del backend debe ser alcanzable desde la red del teléfono (incluido el
APN de la SIM) y se configura al compilar con:

```powershell
flutter build apk --dart-define=API_BASE_URL=https://jamnex-api.cfe.mx/api
```

El hostname es provisional hasta que Infraestructura confirme el nombre DNS
definitivo. La app solo acepta HTTPS. La política de red confía en certificados
del sistema y en `android/app/src/main/res/raw/cfe_ca.crt` para ese hostname/IP.
El certificado incluido actualmente es un placeholder de prueba; reemplázalo
con la CA pública correcta antes de producción. Nunca copies una llave privada
de CA al proyecto ni a la APK.

Las compilaciones Android `debug` pueden usar como último recurso HTTP hacia
`10.14.64.15:8000` para pruebas en la red interna. Las compilaciones `release`
no permiten ese fallback y requieren HTTPS.

Consulta [`../docs/operations.md`](../docs/operations.md) para permisos,
diagnóstico de WorkManager e instalación en un dispositivo.
