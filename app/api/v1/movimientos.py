"""Movimientos de inventario (entradas y salidas)."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.v1.common import a_iso, ahora, exigir_staff, nombre_completo, ordenar, siguiente_id
from app.domain.rules.inventario import aplicar_salida, requiere_alerta
from app.infrastructure.database.session import get_db
from app.models.alerta import Alerta
from app.models.inventario import Inventario
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario

router = APIRouter(prefix="/movimientos", tags=["Movimientos"])

TIPOS = {"entrada": 1, "salida": 2}
ORDEN_MOV = {"fecha": Movimiento.fechaMovimiento, "cantidad": Movimiento.cantidad}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def movimiento_json(m: Movimiento, producto_nombre: str | None) -> dict:
    return {
        "id": m.idMovimiento,
        "producto_id": m.inventario_codInventario,
        "producto_nombre": producto_nombre,
        "tipo": "entrada" if m.tipoMovimiento == TIPOS["entrada"] else "salida",
        "cantidad": m.cantidad,
        "motivo": m.motivo,
        "responsable": m.responsable,
        "fecha": a_iso(m.fechaMovimiento),
    }


def _normalizar_tipo(tipo: str) -> str:
    """Acepta 'Entrada', 'ENTRADA', ' salida ', etc. y devuelve 'entrada' o 'salida'."""
    t = (tipo or "").strip().lower()
    if t not in TIPOS:
        raise HTTPException(status_code=422, detail="El tipo debe ser 'entrada' o 'salida'.")
    return t


def _respuesta(db: Session, creados: list[Movimiento]) -> list[dict]:
    ids = list({m.inventario_codInventario for m in creados})
    nombres = {
        i: n
        for i, n in db.execute(
            select(Inventario.id, Inventario.nombre).where(Inventario.id.in_(ids))
        ).all()
    }
    return [movimiento_json(m, nombres.get(m.inventario_codInventario)) for m in creados]


# ---------------------------------------------------------------------------
# Lógica de negocio
# ---------------------------------------------------------------------------
def aplicar_movimiento(
    db: Session,
    usuario: Usuario,
    producto_id: int,
    tipo: str,
    cantidad: int,
    motivo: str | None,
    responsable: str | None,
    detalle_venta_id: int | None = None,
) -> Movimiento:
    """
    Descuenta o suma stock y registra el movimiento en la MISMA transacción.
    Bloquea la fila del producto para que dos operaciones simultáneas no
    trabajen sobre el mismo stock viejo. No hace commit: lo hace quien llama.
    """
    tipo = _normalizar_tipo(tipo)

    if cantidad is None or cantidad <= 0:
        raise HTTPException(status_code=422, detail="La cantidad debe ser mayor que cero.")

    producto = db.execute(
        select(Inventario).where(Inventario.id == producto_id).with_for_update()
    ).scalar_one_or_none()
    if producto is None:
        raise HTTPException(status_code=404, detail="El producto no existe.")

    stock_actual = producto.stock or 0

    # Reglas A1-A5: cantidad > 0, sin stock negativo, entradas suman, salidas restan.
    if tipo == "salida":
        producto.stock = aplicar_salida(stock_actual, cantidad, producto.nombre)
    else:
        # La entrada simplemente suma al stock (se hace aquí para no depender
        # de la función de dominio, que era el punto donde fallaba).
        producto.stock = stock_actual + cantidad

    precio = producto.precioVenta or 0

    movimiento = Movimiento(
        fechaMovimiento=ahora(),
        precioUnitario=precio,
        cantidad=cantidad,
        subtotal=precio * cantidad,
        tipoMovimiento=TIPOS[tipo],
        usuario_identificacion=usuario.identificacion,
        inventario_codInventario=producto.id,
        detalleVenta_idDetalleVenta=detalle_venta_id,
        motivo=(motivo or "")[:255],
        responsable=(responsable or nombre_completo(usuario))[:120],
    )
    db.add(movimiento)
    db.flush()
    _actualizar_alertas(db, producto)
    return movimiento


def _actualizar_alertas(db: Session, producto: Inventario) -> None:
    """
    Regla A9: al alcanzar el nivel mínimo se genera UNA alerta pendiente por
    producto; cuando el stock se recupera, las alertas pendientes se marcan atendidas.
    """
    pendientes = db.execute(
        select(Alerta).where(
            Alerta.inventario_codInventario == producto.id, Alerta.estado == "pendiente"
        )
    ).scalars().all()

    if requiere_alerta(producto.stock, producto.umbralMinimo):
        if not pendientes:
            mensaje = f"Stock mínimo: {producto.nombre}"
            db.add(
                Alerta(
                    idalertas=siguiente_id(db, Alerta.idalertas),
                    estado="pendiente",
                    mensaje=mensaje[:45],
                    fechaAlerta=ahora(),
                    inventario_codInventario=producto.id,
                )
            )
            db.flush()
    else:
        for alerta in pendientes:
            alerta.estado = "atendida"


def _registrar(
    db: Session,
    usuario: Usuario,
    filas: list[tuple[int, str, int, str | None, str | None]],
) -> list[dict]:
    """Aplica todas las filas en una sola transacción (todo o nada)."""
    creados: list[Movimiento] = []
    try:
        for producto_id, tipo, cantidad, motivo, responsable in filas:
            creados.append(
                aplicar_movimiento(db, usuario, producto_id, tipo, cantidad, motivo, responsable)
            )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        # Devuelve el motivo real (columna NOT NULL, FK, etc.) en vez de un 500 mudo.
        raise HTTPException(
            status_code=400,
            detail=f"Error de base de datos al registrar el movimiento: {getattr(e, 'orig', e)}",
        )
    except Exception:
        db.rollback()
        raise
    return _respuesta(db, creados)


# ---------------------------------------------------------------------------
# Esquemas
# ---------------------------------------------------------------------------
class MovimientoIn(BaseModel):
    """Esquema genérico: el tipo viene en cada fila."""
    producto_id: int
    tipo: Literal["entrada", "salida"]
    cantidad: int = Field(gt=0)
    motivo: str | None = None
    responsable: str | None = None


class MovimientosIn(BaseModel):
    filas: list[MovimientoIn] = Field(min_length=1)


class FilaTipoIn(BaseModel):
    """Esquema para /entrada y /salida: el tipo lo define la ruta."""
    producto_id: int
    cantidad: int = Field(gt=0)
    motivo: str | None = None
    responsable: str | None = None


class FilasTipoIn(BaseModel):
    filas: list[FilaTipoIn] = Field(min_length=1)


def _filas_desde_body(body: "FilasTipoIn | FilaTipoIn", tipo: str):
    """Acepta un solo producto o una lista de filas."""
    items = body.filas if isinstance(body, FilasTipoIn) else [body]
    return [(f.producto_id, tipo, f.cantidad, f.motivo, f.responsable) for f in items]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("", summary="Historial de movimientos")
def listar_movimientos(
    orden: str | None = None, asc: bool = True,
    db: Session = Depends(get_db), _=Depends(exigir_staff),
):
    consulta = select(Movimiento, Inventario.nombre).join(
        Inventario, Inventario.id == Movimiento.inventario_codInventario
    )
    consulta = ordenar(consulta, ORDEN_MOV, orden, asc, Movimiento.idMovimiento)
    return [movimiento_json(m, nombre) for m, nombre in db.execute(consulta).all()]


@router.post("/entrada", summary="Registrar ENTRADA de stock (suma al inventario)")
def registrar_entradas(
    body: FilasTipoIn | FilaTipoIn, db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user), _=Depends(exigir_staff),
):
    return _registrar(db, usuario, _filas_desde_body(body, "entrada"))


@router.post("/salida", summary="Registrar SALIDA de stock (resta del inventario)")
def registrar_salidas(
    body: FilasTipoIn | FilaTipoIn, db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user), _=Depends(exigir_staff),
):
    return _registrar(db, usuario, _filas_desde_body(body, "salida"))


@router.post("", summary="Registrar entradas o salidas mezcladas (ajusta el stock)")
def registrar_movimientos(
    body: MovimientosIn, db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user), _=Depends(exigir_staff),
):
    filas = [(f.producto_id, f.tipo, f.cantidad, f.motivo, f.responsable) for f in body.filas]
    return _registrar(db, usuario, filas)