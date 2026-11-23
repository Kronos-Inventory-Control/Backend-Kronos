"""Movimientos de inventario (entradas y salidas)."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.v1.common import a_iso, ahora, exigir_staff, nombre_completo, ordenar, siguiente_id
from app.domain.rules.inventario import aplicar_entrada, aplicar_salida, requiere_alerta
from app.infrastructure.database.session import get_db
from app.models.alerta import Alerta
from app.models.inventario import Inventario
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario

router = APIRouter(prefix="/movimientos", tags=["Movimientos"])

TIPOS = {"entrada": 1, "salida": 2}
ORDEN_MOV = {"fecha": Movimiento.fechaMovimiento, "cantidad": Movimiento.cantidad}


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
    producto = db.execute(
        select(Inventario).where(Inventario.id == producto_id).with_for_update()
    ).scalar_one_or_none()
    if producto is None:
        raise HTTPException(status_code=404, detail="El producto no existe.")

    # Reglas A1-A5 (app/domain): cantidad > 0, sin stock negativo, entradas suman, salidas restan.
    if tipo == "salida":
        producto.stock = aplicar_salida(producto.stock, cantidad, producto.nombre)
    else:
        producto.stock = aplicar_entrada(producto.stock, cantidad)

    movimiento = Movimiento(
        fechaMovimiento=ahora(),
        precioUnitario=producto.precioVenta,
        cantidad=cantidad,
        subtotal=producto.precioVenta * cantidad,
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


class MovimientoIn(BaseModel):
    producto_id: int
    tipo: Literal["entrada", "salida"]
    cantidad: int = Field(gt=0)
    motivo: str | None = None
    responsable: str | None = None


class MovimientosIn(BaseModel):
    filas: list[MovimientoIn] = Field(min_length=1)


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


@router.post("", summary="Registrar entradas o salidas (ajusta el stock)")
def registrar_movimientos(
    body: MovimientosIn, db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user), _=Depends(exigir_staff),
):
    creados = []
    try:
        for f in body.filas:
            creados.append(
                aplicar_movimiento(
                    db, usuario, f.producto_id, f.tipo, f.cantidad, f.motivo, f.responsable
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    nombres = {
        i: n for i, n in db.execute(
            select(Inventario.id, Inventario.nombre).where(
                Inventario.id.in_(list({m.inventario_codInventario for m in creados}))
            )
        ).all()
    }
    return [movimiento_json(m, nombres.get(m.inventario_codInventario)) for m in creados]
