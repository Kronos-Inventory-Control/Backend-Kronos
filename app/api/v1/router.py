"""
MAPA DE ENDPOINTS (todos cuelgan de /api/v1)

Archivo             Endpoints
------------------  ---------------------------------------------------------------
auth.py             POST /auth/login · GET /auth/me · POST /auth/logout
cuenta.py           POST /auth/register · PATCH /auth/me · POST /auth/change-password
                    POST /auth/change-email · POST /auth/forgot-password
                    POST /auth/reset-password
catalogo.py         GET/POST /productos · PATCH/DELETE /productos/{id}
                    GET/POST /categorias · POST /categorias/eliminar
movimientos.py      GET/POST /movimientos            (POST ajusta el stock)
proveedores.py      GET/POST /proveedores · PATCH/DELETE /proveedores/{id}
ordenes.py          GET/POST /ordenes-compra · PATCH /ordenes-compra/{oc-N | dv-N}
garantias.py        GET/POST /garantias · PATCH/DELETE /garantias/{id}
reportes.py         GET/POST /reportes · DELETE /reportes/{id}
(health.py)         GET /health · GET /health/ready   (fuera de /api/v1)

Utilidades compartidas (roles, ids, fechas): common.py
Documentación interactiva: http://127.0.0.1:8000/docs
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.catalogo import router as catalogo_router
from app.api.v1.cuenta import router as cuenta_router
from app.api.v1.garantias import router as garantias_router
from app.api.v1.movimientos import router as movimientos_router
from app.api.v1.ordenes import router as ordenes_router
from app.api.v1.proveedores import router as proveedores_router
from app.api.v1.reportes import router as reportes_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(cuenta_router)
api_router.include_router(catalogo_router)
api_router.include_router(movimientos_router)
api_router.include_router(proveedores_router)
api_router.include_router(ordenes_router)
api_router.include_router(garantias_router)
api_router.include_router(reportes_router)
