# Kronos Inventory Control - Backend

API en FastAPI + SQLAlchemy + Alembic sobre MySQL.

## Requisitos
Python 3.12 o superior y MySQL con una base `kronos_inventory`.

## Instalación
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # luego editar DATABASE_URL y JWT_SECRET_KEY
```
En la contraseña, `#` se escribe `%23` y `@` se escribe `%40`.

## Base de datos
```sql
CREATE DATABASE IF NOT EXISTS kronos_inventory CHARACTER SET utf8mb4;
```
```powershell
alembic upgrade head
```

## Ejecutar
```powershell
uvicorn app.main:app --reload
```
Documentación en `/docs`; estado en `/health` y `/health/ready`.

## Pruebas
```powershell
pytest
```
Requiere el archivo `.env` creado.

## Autenticación (JWT)
1. Generar la clave y pegarla en `.env` como `JWT_SECRET_KEY` (no se sube a Git):
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
2. Aplicar la migración de autenticación (agrega `activo`, fechas, SUPER_ADMIN único y la tabla `sesionesUsuario`):
```powershell
alembic upgrade head
```
3. Crear el único SUPER_ADMIN (rol 5) desde la terminal:
```powershell
python -m scripts.create_super_admin
```
4. Probar en `/docs`: `POST /api/v1/auth/login` → botón **Authorize** → `GET /api/v1/auth/me` → `POST /api/v1/auth/logout` (204) → `GET /api/v1/auth/me` (401).

Reglas de sesión: token HS256 de 120 min (vencimiento absoluto), 30 min de inactividad, cada sesión tiene un `jti` en MySQL y se revoca individualmente.

## Reglas de negocio (domain)
Las reglas de inventario, ventas, órdenes de compra, garantías y usuarios/roles están en `app/domain/rules/` (Python puro).
Los routers y servicios las llaman; los errores (`app/domain/exceptions.py`) se convierten en HTTP 400 (403 si es un permiso).
Estado de cumplimiento: ver `../REGLAS_DE_NEGOCIO.md`.

## Gestión de usuarios (solo SUPER_ADMIN)
| Método | Endpoint | Función |
|--------|----------|---------|
| POST | `/api/v1/users` | Crear usuario (y su perfil de cliente / proveedor) |
| GET | `/api/v1/users?rol=3&activo=true` | Listar con filtros por rol y estado |
| GET | `/api/v1/users/{identificacion}` | Consultar |
| PATCH | `/api/v1/users/{identificacion}` | Actualizar nombre, apellidos, correo, teléfono (nunca el rol) |
| PATCH | `/api/v1/users/{identificacion}/status` | Activar / desactivar (al desactivar se revocan sus sesiones) |

Ejemplo (proveedor): `{"nombre":"Luis","apellidos":"Pérez","email":"luis@prov.com","password":"ClaveMuySegura2026","rol":"PROVEEDOR","perfil_proveedor":{"tipoProducto":"Herramientas","nit":"900123"}}`.
`rol` acepta el nombre (`CLIENTE`, `PROVEEDOR`, `JEFE`, `EMPLEADO`) o su número. No se puede crear otro SUPER_ADMIN.
