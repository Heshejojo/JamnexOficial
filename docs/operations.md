# Operación y mantenimiento

## 1. Instalación local

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Para producción:

```powershell
npm run build
```

### Móvil

```powershell
cd mobile
flutter pub get
flutter run
flutter build apk --debug
```

La URL del backend debe ser accesible desde el teléfono. `localhost` apunta al
teléfono, no a la computadora. En una red local se usa la IP de la
computadora; en el emulador Android normalmente se usa `10.0.2.2`.

## 2. Variables de entorno

### Backend

```env
SECRET_KEY=valor-secreto
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://usuario:password@host/base?sslmode=require
CORS_ALLOWED_ORIGINS=http://localhost:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173
```

Si `DATABASE_URL` no existe, el proyecto usa SQLite local según la
configuración vigente.

### Frontend

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

La URL compilada de Flutter se configura con el mecanismo
`String.fromEnvironment` utilizado por `ApiService`. Debe proporcionarse al
compilar, por ejemplo:

```powershell
flutter build apk --dart-define=API_BASE_URL=https://api.example.com/api
```

## 3. Migraciones

Cada vez que cambien modelos:

```powershell
cd backend
python manage.py makemigrations
python manage.py migrate
```

La migración crítica para el consumo por SIM es:

```text
consumos/migrations/0003_consumosyncstate_sim_scope.py
```

Esa migración reemplaza la unicidad `dispositivo + fecha` por
`dispositivo + fecha + sim`. Debe ejecutarse antes de recibir nuevos consumos
de equipos con dos SIMs.

## 4. Despliegue

En producción:

1. Respaldar la base de datos.
2. Instalar dependencias.
3. Configurar variables secretas.
4. Ejecutar migraciones.
5. Construir el frontend.
6. Servir Django con Gunicorn detrás de HTTPS.
7. Servir los archivos estáticos con WhiteNoise o un proxy.
8. Configurar CORS y CSRF con dominios concretos.
9. Compilar la APK con la URL de producción.
10. Probar un dispositivo real y revisar el primer registro.

No deben publicarse `.env`, tokens de dispositivo, claves JWT ni contraseñas.

## 5. Diagnóstico de sincronización Android

### Síntoma: no reporta al conectar Wi-Fi o datos móviles

1. Abrir la app una vez después de instalarla.
2. Confirmar que el APN de la SIM está configurado por el operador y que el
   backend responde desde el navegador del dispositivo usando esa conexión.
3. Confirmar que `API_BASE_URL` en la APK apunta al backend, no al puerto de
   Vite; en desarrollo Django usa el puerto `8000`.
4. Revisar que la aplicación no esté en “Forzar detención”.
5. Quitar restricciones de batería:
   `Ajustes > Aplicaciones > Jamnex > Batería > Sin restricciones`.
6. Confirmar que la red permita llegar al servidor; una IP privada solo será
   accesible si el APN enruta a esa red.
7. Revisar el estado de WorkManager:

```powershell
adb shell dumpsys jobscheduler
adb logcat -d | Select-String "JamnexSyncWorker|Worker result"
```

Un resultado correcto aparece como:

```text
Worker result SUCCESS
```

### Síntoma: la app muestra consumo, pero el panel no

1. Revisar que el dispositivo haya completado una sincronización.
2. Consultar `/api/consumos/`.
3. Confirmar que el registro tenga la SIM y el dispositivo correctos.
4. Revisar `ConsumoSyncState` si el contador Android bajó o se reinició.
5. Actualizar la vista web; el panel de SIM recalcula cada vez que consulta
   consumos y dispositivos.

### Síntoma: consumo duplicado

Revisar que la migración `0003_consumosyncstate_sim_scope` esté aplicada y que
el registro se identifique por SIM. No se debe borrar manualmente el consumo
antes de revisar el contador de sincronización.

## 6. Verificación previa a una entrega

```powershell
# Backend
cd backend
python manage.py check
python manage.py test

# Frontend
cd ..\frontend
npm run build

# Móvil
cd ..\mobile
flutter analyze
flutter build apk --debug
```

Después de compilar la APK:

```powershell
adb devices
adb install -r build\app\outputs\flutter-apk\app-debug.apk
adb shell monkey -p com.example.agente_cfe 1
```

Validar manualmente:

- Registro inicial del dispositivo.
- Detección de una y dos SIMs.
- Consumo diario.
- Cambio entre Wi-Fi y datos móviles.
- Sincronización con la app en segundo plano.
- Baja y reactivación de SIM.
- Exportación mensual.

## 7. Consideraciones de Android

`NetworkStatsManager` puede devolver cero o no devolver datos cuando Android no
permite consultar estadísticas, falta acceso de uso, no se identifica la
suscripción o no existe consumo móvil en el día actual. Un cero del día no
borra consumos anteriores del backend.

WorkManager es un mecanismo garantizado de ejecución eventual, no un reloj de
precisión. El sistema puede retrasar trabajos por batería, modo reposo,
políticas del fabricante o conectividad aún no validada.
