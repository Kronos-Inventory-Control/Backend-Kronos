"""
MAPA DE ENDPOINTS (todos cuelgan de /api/v1)

Archivo           Endpoints
--------------------------------------------------------------------------------
auth.py           POST /auth/login · GET /auth/me · POST /auth/logout
cuenta.py         POST /auth/register · PATCH/DELETE /auth/me · POST /auth/change-password
                  POST /auth/change-email · POST /auth/confirm-email
                  POST /auth/forgot-password · POST /auth/verify-reset-code
                  POST /auth/reset-password
catalogo.py       GET/POST /productos · PATCH/DELETE /productos/{id} · GET /productos/{id}/imagen
                  GET/POST /categorias · POST /categorias/eliminar
movimientos.py    GET/POST /movimientos         (POST ajusta el stock)
proveedores.py    GET/POST /proveedores · PATCH/DELETE /proveedores/{id}
ordenes.py        GET/POST /ordenes-compra · PATCH /ordenes-compra/{oc-N | dv-N}
garantias.py      GET/POST /garantias · PATCH/DELETE /garantias/{id}
reportes.py       GET/POST /reportes · DELETE /reportes/{id}
users.py          POST/GET /users · GET/PATCH /users/{id} · PATCH /users/{id}/status  (solo SUPER_ADMIN)
(health.py)       GET /health · GET /health/ready   (fuera de /api/v1)

Utilidades compartidas (roles, ids, fechas): common.py
Documentación interactiva: http://127.0.0.1:8000/docs
"""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    catalogo,
    cuenta,
    garantias,
    movimientos,
    ordenes,
    proveedores,
    reportes,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(cuenta.router)
api_router.include_router(catalogo.router)
api_router.include_router(movimientos.router)
api_router.include_router(proveedores.router)
api_router.include_router(ordenes.router)
api_router.include_router(garantias.router)
api_router.include_router(reportes.router)
api_router.include_router(users.router)