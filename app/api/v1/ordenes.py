"""
Órdenes de compra.

El frontend las trata como una sola lista, pero en MySQL viven en dos tablas:
- `ordenesCompra`: órdenes del jefe a un proveedor (origen "interno").
- `ventas` + `detalleVentas`: compras de los clientes (origen "cliente").

Para no mezclar ids, cada fila lleva un prefijo: `oc-12` o `dv-34`.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.v1.common import (
    a_iso,
    ahora,
    es_staff,
    nombre_completo,
    num,
    obtener_o_crear_cliente,
    proveedor_de,
    siguiente_id,
)
from app.api.v1.movimientos import aplicar_movimiento
from app.domain.enums.user_role import UserRole
from app.domain.rules.usuarios import proveedor_gestiona_orden
from app.domain.rules.ventas import validar_linea_venta, validar_venta
from app.infrastructure.database.session import get_db
from app.models.cliente import Cliente
from app.models.detalle_venta import DetalleVenta
from app.models.inventario import Inventario
from app.models.orden_compra import OrdenCompra
from app.models.proveedor import Proveedor
from app.models.usuario import Usuario
from app.models.venta import Venta

router = APIRouter(prefix="/ordenes-compra", tags=["Órdenes de compra"])


# ------------------------------------------------------------ consultas/json
def _consulta_oc():
    return (
        select(OrdenCompra, Inventario.nombre, Usuario)
        .join(Inventario, Inventario.id == OrdenCompra.inventario_codInventario)
        .join(Proveedor, Proveedor.idProveedor == OrdenCompra.proveedor_idProveedor)
        .join(Usuario, Usuario.identificacion == Proveedor.usuario_identificacion)
    )


def _consulta_dv():
    return (
        select(DetalleVenta, Venta, Inventario.nombre, Usuario)
        .join(Venta, Venta.idVenta == DetalleVenta.venta_idVenta)
        .join(Inventario, Inventario.id == DetalleVenta.inventario_codInventario)
        .join(Cliente, Cliente.idCliente == Venta.cliente_idCliente)
        .join(Usuario, Usuario.identificacion == Cliente.usuario_identificacion)
    )


def _json_oc(oc: OrdenCompra, producto: str, prov: Usuario) -> dict:
    return {
        "id": f"oc-{oc.idOrdenesCompra}",
        "codigo": oc.codigo,
        "producto_id": oc.inventario_codInventario,
        "producto_nombre": producto,
        "cantidad": oc.cantidad,
        "proveedor_id": oc.proveedor_idProveedor,
        "proveedor_nombre": nombre_completo(prov),
        "cliente_id": None,
        "cliente_nombre": None,
        "precio_unitario": num(oc.precioUnitario),
        "origen": "interno",
        "estado": oc.estado,
        "observacion": oc.observacion,
        "fecha": a_iso(oc.fechaOrden),
    }


def _json_dv(dv: DetalleVenta, venta: Venta, producto: str, cliente: Usuario) -> dict:
    return {
        "id": f"dv-{dv.idDetalleVenta}",
        "codigo": dv.codigo,
        "producto_id": dv.inventario_codInventario,
        "producto_nombre": producto,
        "cantidad": dv.cantidad,
        "proveedor_id": None,
        "proveedor_nombre": None,
        "cliente_id": cliente.identificacion,
        "cliente_nombre": nombre_completo(cliente),
        "precio_unitario": num(dv.precioUnitario),
        "origen": "cliente",
        "estado": dv.estado,
        "observacion": dv.observacion,
        "fecha": a_iso(venta.fechaVenta),
    }


def _fila_por_ref(db: Session, prefijo: str, numero: int) -> dict:
    if prefijo == "oc":
        fila = db.execute(_consulta_oc().where(OrdenCompra.idOrdenesCompra == numero)).first()
        if fila:
            return _json_oc(*fila)
    elif prefijo == "dv":
        fila = db.execute(_consulta_dv().where(DetalleVenta.idDetalleVenta == numero)).first()
        if fila:
            return _json_dv(*fila)
    raise HTTPException(status_code=404, detail="La orden no existe.")


def _separar_ref(ref: str) -> tuple[str, int]:
    prefijo, _, texto = ref.partition("-")
    if prefijo not in ("oc", "dv") or not texto.isdigit():
        raise HTTPException(status_code=404, detail="La orden no existe.")
    return prefijo, int(texto)


# ------------------------------------------------------------------- listar
@router.get("", summary="Lista de órdenes (filtrada según el rol)")
def listar_ordenes(
    proveedor_id: int | None = None,
    cliente_id: int | None = None,
    orden: str | None = None,
    asc: bool = False,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    incluir_oc = incluir_dv = True
    if es_staff(usuario):
        if proveedor_id is not None:
            incluir_dv = False
        if cliente_id is not None:
            incluir_oc = False
    elif usuario.rol_idRol == int(UserRole.PROVEEDOR):
        incluir_dv = False
        propio = proveedor_de(db, usuario)
        if propio is None:
            return []
        proveedor_id = propio.idProveedor
    elif usuario.rol_idRol == int(UserRole.CLIENTE):
        incluir_oc = False
        cliente_id = usuario.identificacion
    else:
        raise HTTPException(status_code=403, detail="No tienes permiso para esta operación.")

    filas: list[tuple[datetime | None, dict]] = []
    if incluir_oc:
        consulta = _consulta_oc()
        if proveedor_id is not None:
            consulta = consulta.where(OrdenCompra.proveedor_idProveedor == proveedor_id)
        for oc, producto, prov in db.execute(consulta).all():
            filas.append((oc.fechaOrden, _json_oc(oc, producto, prov)))
    if incluir_dv:
        consulta = _consulta_dv()
        if cliente_id is not None:
            consulta = consulta.where(Usuario.identificacion == cliente_id)
        for dv, venta, producto, cliente in db.execute(consulta).all():
            filas.append((venta.fechaVenta, _json_dv(dv, venta, producto, cliente)))

    filas.sort(key=lambda par: par[0] or datetime.min, reverse=not asc)
    return [fila for _, fila in filas]


# -------------------------------------------------------------------- crear
class OrdenIn(BaseModel):
    codigo: str | None = Field(default=None, max_length=45)
    producto_id: int
    cantidad: int = Field(gt=0)
    proveedor_id: int | None = None
    precio_unitario: float | None = Field(default=None, ge=0)
    origen: Literal["interno", "cliente"] = "interno"
    observacion: str | None = Field(default=None, max_length=255)


class OrdenesIn(BaseModel):
    filas: list[OrdenIn] = Field(min_length=1)


def _bloquear_producto(db: Session, producto_id: int) -> Inventario:
    producto = db.execute(
        select(Inventario).where(Inventario.id == producto_id).with_for_update()
    ).scalar_one_or_none()
    if producto is None:
        raise HTTPException(status_code=404, detail="Uno de los productos ya no existe.")
    return producto


@router.post("", summary="Crear órdenes a proveedor o compras de cliente")
def crear_ordenes(
    body: OrdenesIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    origenes = {f.origen for f in body.filas}
    if len(origenes) > 1:
        raise HTTPException(status_code=400, detail="No se pueden mezclar órdenes internas y de cliente.")
    origen = origenes.pop()
    referencias: list[tuple[str, int]] = []

    try:
        if origen == "interno":
            if not es_staff(usuario):
                raise HTTPException(status_code=403, detail="No tienes permiso para esta operación.")
            for f in body.filas:
                if f.proveedor_id is None:
                    raise HTTPException(status_code=400, detail="Selecciona un proveedor para cada material.")
                if db.execute(
                    select(Proveedor.idProveedor).where(Proveedor.idProveedor == f.proveedor_id)
                ).first() is None:
                    raise HTTPException(status_code=400, detail="El proveedor seleccionado no existe.")
                producto = _bloquear_producto(db, f.producto_id)
                orden = OrdenCompra(
                    idOrdenesCompra=siguiente_id(db, OrdenCompra.idOrdenesCompra),
                    codigo=f.codigo or f"OC-{int(ahora().timestamp())}-{producto.id}",
                    fechaOrden=ahora(),
                    cantidad=f.cantidad,
                    precioUnitario=Decimal(str(f.precio_unitario or 0)),
                    estado="pendiente",
                    observacion=f.observacion,
                    proveedor_idProveedor=f.proveedor_id,
                    inventario_codInventario=producto.id,
                )
                db.add(orden)
                db.flush()
                referencias.append(("oc", orden.idOrdenesCompra))
        else:
            if usuario.rol_idRol != int(UserRole.CLIENTE):
                raise HTTPException(
                    status_code=403,
                    detail="Esta cuenta no está habilitada para compras. Usa una cuenta de cliente.",
                )
            cliente = obtener_o_crear_cliente(db, usuario)
            validar_venta(len(body.filas), cliente.idCliente)  # B3 + B6
            venta = Venta(
                descuento=Decimal("0"),
                fechaVenta=ahora(),
                estado="pendiente",
                totalVenta=Decimal("0"),
                comprobantePago="",
                metodoPago="Por definir",
                cliente_idCliente=cliente.idCliente,
            )
            db.add(venta)
            db.flush()

            total = Decimal("0")
            for f in body.filas:
                producto = _bloquear_producto(db, f.producto_id)
                precio = Decimal(str(f.precio_unitario)) if f.precio_unitario is not None else producto.precioVenta
                # B1 + B2 + B4 (y A6): cantidad > 0, precio >= 0, hay stock y no está agotado.
                validar_linea_venta(f.cantidad, precio, producto.stock, producto.nombre)
                subtotal = precio * f.cantidad
                total += subtotal
                detalle = DetalleVenta(
                    subTotal=subtotal,
                    cantidad=f.cantidad,
                    precioUnitario=precio,
                    venta_idVenta=venta.idVenta,
                    inventario_codInventario=producto.id,
                    codigo=f.codigo,
                    estado="pendiente",
                )
                db.add(detalle)
                db.flush()
                aplicar_movimiento(
                    db, usuario, producto.id, "salida", f.cantidad,
                    f"Venta en línea · Pedido {f.codigo or detalle.idDetalleVenta} · {producto.nombre}",
                    f"Cliente: {nombre_completo(usuario) or 'sin nombre'}",
                    detalle_venta_id=detalle.idDetalleVenta,
                )
                referencias.append(("dv", detalle.idDetalleVenta))
            venta.totalVenta = total
        db.commit()
    except Exception:
        db.rollback()
        raise

    return [_fila_por_ref(db, prefijo, numero) for prefijo, numero in referencias]


# ---------------------------------------------------------------- actualizar
class OrdenPatch(BaseModel):
    estado: Literal["pendiente", "confirmada", "rechazada"] | None = None
    observacion: str | None = Field(default=None, max_length=255)


@router.patch("/{ref}", summary="Cambiar el estado u observación de una orden")
def actualizar_orden(
    ref: str, body: OrdenPatch,
    db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user),
):
    prefijo, numero = _separar_ref(ref)
    datos = body.model_dump(exclude_unset=True)

    try:
        if prefijo == "oc":
            orden = db.get(OrdenCompra, numero)
            if orden is None:
                raise HTTPException(status_code=404, detail="La orden no existe.")
            propio = proveedor_de(db, usuario) if usuario.rol_idRol == int(UserRole.PROVEEDOR) else None
            if not (
                es_staff(usuario)
                or proveedor_gestiona_orden(propio.idProveedor if propio else None, orden.proveedor_idProveedor)
            ):  # E4
                raise HTTPException(status_code=403, detail="No tienes permiso para esta operación.")
            if datos.get("estado"):
                orden.estado = datos["estado"]
            if "observacion" in datos:
                orden.observacion = datos["observacion"]
        else:
            if not es_staff(usuario):
                raise HTTPException(status_code=403, detail="No tienes permiso para esta operación.")
            detalle = db.get(DetalleVenta, numero)
            if detalle is None:
                raise HTTPException(status_code=404, detail="La orden no existe.")
            nuevo = datos.get("estado")
            if nuevo and nuevo != detalle.estado:
                if nuevo == "rechazada":
                    # Pedido rechazado: el material vuelve al inventario.
                    aplicar_movimiento(
                        db, usuario, detalle.inventario_codInventario, "entrada", detalle.cantidad,
                        f"Devolución por pedido rechazado · {detalle.codigo or detalle.idDetalleVenta}",
                        "Sistema", detalle_venta_id=detalle.idDetalleVenta,
                    )
                elif detalle.estado == "rechazada":
                    # Se reactiva un pedido rechazado: se descuenta de nuevo.
                    aplicar_movimiento(
                        db, usuario, detalle.inventario_codInventario, "salida", detalle.cantidad,
                        f"Pedido reactivado · {detalle.codigo or detalle.idDetalleVenta}",
                        "Sistema", detalle_venta_id=detalle.idDetalleVenta,
                    )
                detalle.estado = nuevo
            if "observacion" in datos:
                detalle.observacion = datos["observacion"]
        db.commit()
    except Exception:
        db.rollback()
        raise

    return [_fila_por_ref(db, prefijo, numero)]
