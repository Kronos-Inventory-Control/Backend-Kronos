"""
MAPA DE ENDPOINTS (todos cuelgan de /api/v1)

Archivo             Endpoints
------------------  ---------------------------------------------------------------
auth.py             POST /auth/login · GET /auth/me · POST /auth/logout
cuenta.py           POST /auth/register · PATCH/DELETE /auth/me · POST /auth/change-password
                    POST /auth/change-email · POST /auth/confirm-email
                    POST /auth/forgot-password · POST /auth/verify-reset-code
                    POST /auth/reset-password
catalogo.py         GET/POST /productos · PATCH/DELETE /productos/{id} · GET /productos/{id}/imagen
                    GET/POST /categorias · POST /categorias/eliminar
movimientos.py      GET/POST /movimientos            (POST ajusta el stock)
proveedores.py      GET/POST /proveedores · PATCH/DELETE /proveedores/{id}
ordenes.py          GET/POST /ordenes-compra · PATCH /ordenes-compra/{oc-N | dv-N}
garantias.py        GET/POST /garantias · PATCH/DELETE /garantias/{id}
reportes.py         GET/POST /reportes · DELETE /reportes/{id}
users.py            POST/GET /users · GET/PATCH /users/{id} · PATCH /users/{id}/status   (solo SUPER_ADMIN)
(health.py)         GET /health · GET /health/ready   (fuera de /api/v1)

Utilidades compartidas (roles, ids, fechas): common.py
Documentación interactiva: http://127.0.0.1:8000/docs
"""
from fastapi import APIRouter

api_router = APIRouter()

# En las siguientes fases registraremos aquí los routers de
# auth, productos, movimientos, proveedores, órdenes, garantías, etc.