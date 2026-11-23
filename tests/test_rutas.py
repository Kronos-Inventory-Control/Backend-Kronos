from datetime import datetime

from app.api.v1.common import a_iso
from app.main import app

RUTAS_ESPERADAS = {
    ("GET", "/api/v1/productos"),
    ("POST", "/api/v1/productos"),
    ("PATCH", "/api/v1/productos/{producto_id}"),
    ("DELETE", "/api/v1/productos/{producto_id}"),
    ("GET", "/api/v1/categorias"),
    ("POST", "/api/v1/categorias"),
    ("POST", "/api/v1/categorias/eliminar"),
    ("GET", "/api/v1/movimientos"),
    ("POST", "/api/v1/movimientos"),
    ("GET", "/api/v1/proveedores"),
    ("POST", "/api/v1/proveedores"),
    ("PATCH", "/api/v1/proveedores/{proveedor_id}"),
    ("DELETE", "/api/v1/proveedores/{proveedor_id}"),
    ("GET", "/api/v1/ordenes-compra"),
    ("POST", "/api/v1/ordenes-compra"),
    ("PATCH", "/api/v1/ordenes-compra/{ref}"),
    ("GET", "/api/v1/garantias"),
    ("POST", "/api/v1/garantias"),
    ("PATCH", "/api/v1/garantias/{garantia_id}"),
    ("DELETE", "/api/v1/garantias/{garantia_id}"),
    ("GET", "/api/v1/reportes"),
    ("POST", "/api/v1/reportes"),
    ("DELETE", "/api/v1/reportes/{reporte_id}"),
    ("POST", "/api/v1/auth/register"),
    ("PATCH", "/api/v1/auth/me"),
    ("POST", "/api/v1/auth/change-password"),
    ("POST", "/api/v1/auth/change-email"),
    ("POST", "/api/v1/auth/forgot-password"),
    ("POST", "/api/v1/auth/reset-password"),
    ("POST", "/api/v1/users"),
    ("GET", "/api/v1/users"),
    ("GET", "/api/v1/users/{identificacion}"),
    ("PATCH", "/api/v1/users/{identificacion}"),
    ("PATCH", "/api/v1/users/{identificacion}/status"),
}


def _rutas_registradas():
    return {(m, r.path) for r in app.routes if hasattr(r, "methods") for m in r.methods}


def test_estan_registrados_todos_los_endpoints_de_la_migracion():
    faltantes = RUTAS_ESPERADAS - _rutas_registradas()
    assert not faltantes, f"Faltan rutas: {sorted(faltantes)}"


def test_fechas_se_serializan_en_utc():
    assert a_iso(datetime(2026, 11, 17, 12, 30)) == "2026-11-17T12:30:00Z"
    assert a_iso(None) is None
