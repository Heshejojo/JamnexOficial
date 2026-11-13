# Backend - Django + DRF

Este directorio contiene la API y la lógica de persistencia de JamnexCFE.
La documentación funcional completa está en [`../docs/architecture.md`](../docs/architecture.md)
y la referencia de endpoints en [`../docs/api-reference.md`](../docs/api-reference.md).

## Responsabilidades

- Autenticación JWT para usuarios del panel.
- Credenciales separadas para agentes Android.
- Registro de dispositivos, telemetría y conectividad.
- Detección, baja, reactivación, transferencia e historial de SIMs.
- Acumulación diaria de consumo por dispositivo y SIM.
- Dashboard, exportación Excel y auditoría.

## Base de datos

El backend usa PostgreSQL cuando `DATABASE_URL` está definida en `backend/.env`. La URL puede apuntar a PostgreSQL 17 o a Neon y debe incluir `sslmode=require` cuando el proveedor lo solicite. Si no existe, se usa SQLite local como respaldo.

```env
DATABASE_URL=postgresql://usuario:contraseña@host/neondb?sslmode=require
```

Una vez configurada la URL, ejecuta:

```powershell
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

El módulo `areas` administra distribuciones (`procesos`), divisiones
(`subprocesos`) y zonas (`areas`). Las migraciones `0002` y `0003` preparan
esas tablas y sus relaciones; `dispositivos.0004` agrega la asignación opcional
de cada terminal a una zona. Las tablas puente `procesos_zona` y
`areas_procesos_zona` se conservan. Aplica los cambios con
`python manage.py migrate`.

## Apps Django

`usuarios`, `areas`, `trabajadores`, `dispositivos`, `sims`, `consumos`,
`redes`, `bateria`, `ram`, `almacenamiento`, `operadores`, `reportes` y
`auditoria` separan cada dominio para que sus modelos, rutas y migraciones
sean mantenibles de forma independiente.

## Comandos habituales

```powershell
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py test
python manage.py runserver
```
