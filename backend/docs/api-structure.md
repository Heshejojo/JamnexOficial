# Estructura y diseño API inicial

## Endpoints previstos

- POST /api/auth/login/
- POST /api/auth/refresh/
- GET /api/trabajadores/
- GET /api/trabajadores/{id}/
- GET /api/dispositivos/
- GET /api/dispositivos/{id}/
- GET /api/sims/
- GET /api/sims/{id}/
- POST /api/device/register/
- POST /api/device/status/
- POST /api/device/consumption/
- GET /api/consumos/
- GET /api/redes/
- GET /api/reportes/sims/{id}/exportar/
- GET /api/reportes/dispositivos/exportar/

## Autenticación

- JWT con access + refresh token.
- Roles y permisos sobre endpoints.
- Dispositivos con identidad propia y token restringido.

## Reglas actuales

- No se ejecutan migraciones ni configuraciones de producción.
- Este documento sirve como base de diseño para la fase 2.
