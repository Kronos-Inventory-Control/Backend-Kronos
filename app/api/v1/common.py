"""
Utilidades compartidas por los routers de Kronos.

Las respuestas de la API mantienen los mismos nombres de campo que el
frontend ya usaba (stock_actual, umbral_minimo, proveedor_nombre...), para
que las pantallas no tengan que conocer los nombres de columna de MySQL.
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.domain.enums.user_role import UserRole
from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.marca import Marca
from app.models.proveedor import Proveedor
from app.models.unidad_venta import UnidadVenta
from app.models.usuario import Usuario
from app.repositories.user_repository import UserRepository

SIN_CATEGORIA = "Sin categoría"
ESTADOS_ORDEN = ("pendiente", "confirmada", "rechazada")
ROLES_STAFF = (UserRole.JEFE, UserRole.EMPLEADO, UserRole.SUPER_ADMIN)


def ahora() -> datetime:
    """Fecha actual en UTC sin zona horaria (como las columnas DateTime)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def a_iso(valor: datetime | None) -> str | None:
    """Fecha en ISO 8601 con 'Z' para que el navegador la convierta a su hora local."""
    if valor is None:
        return None
    return valor.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def num(valor: Decimal | int | float | None) -> float | None:
    return float(valor) if valor is not None else None


def exigir_roles(*roles: UserRole):
    """Dependencia: deja pasar solo a los roles indicados."""
    permitidos = {int(r) for r in roles}

    def dependencia(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol_idRol not in permitidos:
            raise HTTPException(status_code=403, detail="No tienes permiso para esta operación.")
        return usuario

    return dependencia


exigir_staff = exigir_roles(*ROLES_STAFF)


def es_staff(usuario: Usuario) -> bool:
    return usuario.rol_idRol in {int(r) for r in ROLES_STAFF}


def siguiente_id(db: Session, columna) -> int:
    """
    Siguiente id para tablas cuya clave primaria no es AUTO_INCREMENT.
    Bloquea el final del índice para que dos peticiones simultáneas no
    obtengan el mismo número.
    """
    maximo = db.execute(select(func.max(columna)).with_for_update()).scalar()
    return int(maximo or 0) + 1


def nombre_completo(usuario: Usuario | None) -> str:
    if usuario is None:
        return ""
    return f"{usuario.nombre} {usuario.apellidos}".strip()


def obtener_o_crear_categoria(db: Session, nombre: str) -> Categoria:
    nombre = nombre.strip()
    categoria = db.execute(
        select(Categoria).where(Categoria.nombreCategoria == nombre)
    ).scalars().first()
    if categoria is None:
        categoria = Categoria(idCategoria=siguiente_id(db, Categoria.idCategoria), nombreCategoria=nombre)
        db.add(categoria)
        db.flush()
    return categoria


def obtener_o_crear_marca(db: Session, nombre: str = "Genérica") -> Marca:
    marca = db.execute(select(Marca).where(Marca.nombreMarca == nombre)).scalars().first()
    if marca is None:
        marca = Marca(nombreMarca=nombre)
        db.add(marca)
        db.flush()
    return marca


def obtener_o_crear_unidad(db: Session, nombre: str = "Unidad") -> UnidadVenta:
    unidad = db.execute(
        select(UnidadVenta).where(UnidadVenta.nombreUnidadMedida == nombre)
    ).scalars().first()
    if unidad is None:
        unidad = UnidadVenta(
            idUnidadVenta=siguiente_id(db, UnidadVenta.idUnidadVenta), nombreUnidadMedida=nombre
        )
        db.add(unidad)
        db.flush()
    return unidad


def obtener_o_crear_cliente(db: Session, usuario: Usuario) -> Cliente:
    cliente = db.execute(
        select(Cliente).where(Cliente.usuario_identificacion == usuario.identificacion)
    ).scalars().first()
    if cliente is None:
        cliente = Cliente(carritoActivo=False, usuario_identificacion=usuario.identificacion)
        db.add(cliente)
        db.flush()
    return cliente


def ordenar(consulta, columnas: dict, orden: str | None, asc: bool, defecto):
    """Aplica ORDER BY usando solo columnas permitidas (evita ordenar por texto libre)."""
    columna = columnas.get(orden or "", defecto)
    return consulta.order_by(columna.asc() if asc else columna.desc())


def siguiente_identificacion(db: Session) -> int:
    """Identificación (cédula/NIT interno) para usuarios creados desde la app."""
    return UserRepository.next_identificacion(db)


def proveedor_de(db: Session, usuario: Usuario) -> Proveedor | None:
    """Ficha de proveedor vinculada al usuario (si su rol es proveedor)."""
    return db.execute(
        select(Proveedor).where(Proveedor.usuario_identificacion == usuario.identificacion)
    ).scalars().first()
