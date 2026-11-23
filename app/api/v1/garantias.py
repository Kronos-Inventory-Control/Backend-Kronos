"""Solicitudes de garantía."""

import json
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.v1.common import a_iso, ahora, es_staff, exigir_staff, ordenar, proveedor_de
from app.domain.enums.user_role import UserRole
from app.infrastructure.database.session import get_db
from app.models.detalle_venta import DetalleVenta
from app.models.garantia import Garantia
from app.models.orden_compra import OrdenCompra
from app.models.usuario import Usuario

router = APIRouter(prefix="/garantias", tags=["Garantías"])

ORDEN_GAR = {"fecha": Garantia.fechaInicio, "estado": Garantia.estado}


def _lista(texto: str | None) -> list:
    try:
        valor = json.loads(texto) if texto else []
    except ValueError:
        return []
    return valor if isinstance(valor, list) else []


def garantia_json(g: Garantia) -> dict:
    return {
        "id": g.idGarantia,
        "orden_id": g.ordenRef,
        "numero_orden": g.numeroOrden,
        "cliente_id": g.clienteId,
        "cliente_nombre": g.clienteNombre,
        "cliente_destino": g.clienteNombre,
        "correo": g.correo,
        "producto": g.producto,
        "motivo": g.motivo,
        "estado": g.estado,
        "observacion": g.observacion,
        "imagen_nombre": g.imagenNombre,
        "observaciones": _lista(g.observaciones),
        "bitacora": _lista(g.bitacora),
        "fecha": a_iso(g.fechaInicio),
    }


def _refs_del_proveedor(db: Session, usuario: Usuario) -> list[str]:
    propio = proveedor_de(db, usuario)
    if propio is None:
        return []
    ids = db.execute(
        select(OrdenCompra.idOrdenesCompra).where(OrdenCompra.proveedor_idProveedor == propio.idProveedor)
    ).scalars().all()
    return [f"oc-{i}" for i in ids]


def _puede_ver(db: Session, usuario: Usuario, g: Garantia) -> bool:
    if es_staff(usuario):
        return True
    if usuario.rol_idRol == int(UserRole.CLIENTE):
        return g.clienteId == usuario.identificacion
    if usuario.rol_idRol == int(UserRole.PROVEEDOR):
        return g.ordenRef in _refs_del_proveedor(db, usuario)
    return False


@router.get("", summary="Garantías visibles para el usuario")
def listar_garantias(
    orden: str | None = None, asc: bool = False,
    db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user),
):
    consulta = select(Garantia)
    if es_staff(usuario):
        pass
    elif usuario.rol_idRol == int(UserRole.CLIENTE):
        consulta = consulta.where(Garantia.clienteId == usuario.identificacion)
    elif usuario.rol_idRol == int(UserRole.PROVEEDOR):
        refs = _refs_del_proveedor(db, usuario)
        if not refs:
            return []
        consulta = consulta.where(Garantia.ordenRef.in_(refs))
    else:
        raise HTTPException(status_code=403, detail="No tienes permiso para esta operación.")
    consulta = ordenar(consulta, ORDEN_GAR, orden, asc, Garantia.idGarantia)
    return [garantia_json(g) for g in db.execute(consulta).scalars().all()]


class GarantiaIn(BaseModel):
    orden_id: str | None = Field(default=None, max_length=20)
    numero_orden: str | None = Field(default=None, max_length=60)
    cliente_id: int | None = None
    cliente_nombre: str | None = Field(default=None, max_length=120)
    correo: str | None = Field(default=None, max_length=120)
    producto: str | None = Field(default=None, max_length=120)
    motivo: str = Field(min_length=1)
    observacion: str | None = None
    imagen_nombre: str | None = Field(default=None, max_length=255)
    estado: str = Field(default="pendiente", max_length=45)
    observaciones: list = Field(default_factory=list)
    bitacora: list = Field(default_factory=list)


class GarantiasIn(BaseModel):
    filas: list[GarantiaIn] = Field(min_length=1)


class GarantiaPatch(BaseModel):
    estado: str | None = Field(default=None, max_length=45)
    observacion: str | None = None
    motivo: str | None = None
    imagen_nombre: str | None = Field(default=None, max_length=255)
    observaciones: list | None = None
    bitacora: list | None = None


@router.post("", summary="Radicar solicitudes de garantía")
def crear_garantias(
    body: GarantiasIn, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user),
):
    es_cliente = usuario.rol_idRol == int(UserRole.CLIENTE)
    if not (es_cliente or es_staff(usuario)):
        raise HTTPException(status_code=403, detail="No tienes permiso para esta operación.")

    creadas = []
    try:
        for f in body.filas:
            detalle_id = None
            if f.orden_id and f.orden_id.startswith("dv-") and f.orden_id[3:].isdigit():
                detalle = db.get(DetalleVenta, int(f.orden_id[3:]))
                detalle_id = detalle.idDetalleVenta if detalle else None

            inicio = ahora()
            garantia = Garantia(
                fechaInicio=inicio,
                fechaFin=inicio + timedelta(days=365),
                estado=f.estado,
                observacion=f.observacion or "",
                motivo=f.motivo,
                tipoFalla=(f.motivo.split(":")[0].strip()[:45] if ":" in f.motivo else ""),
                evidenciaImg=None,
                detalleventa_idDetalleVenta=detalle_id,
                ordenRef=f.orden_id,
                numeroOrden=f.numero_orden,
                clienteId=usuario.identificacion if es_cliente else f.cliente_id,
                clienteNombre=f.cliente_nombre,
                correo=f.correo,
                producto=f.producto,
                imagenNombre=f.imagen_nombre,
                observaciones=json.dumps(f.observaciones, ensure_ascii=False),
                bitacora=json.dumps(f.bitacora, ensure_ascii=False),
            )
            db.add(garantia)
            db.flush()
            creadas.append(garantia)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return [garantia_json(g) for g in creadas]


@router.patch("/{garantia_id}", summary="Actualizar una garantía")
def actualizar_garantia(
    garantia_id: int, body: GarantiaPatch,
    db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user),
):
    garantia = db.get(Garantia, garantia_id)
    if garantia is None or not _puede_ver(db, usuario, garantia):
        raise HTTPException(status_code=404, detail="La garantía no existe.")

    datos = body.model_dump(exclude_unset=True)
    rol = usuario.rol_idRol
    if rol == int(UserRole.CLIENTE):
        # El cliente edita su solicitud o la cancela; no aprueba ni rechaza.
        if datos.get("estado") not in (None, "cancelada"):
            raise HTTPException(status_code=403, detail="Solo puedes cancelar tu solicitud.")
    elif rol == int(UserRole.PROVEEDOR):
        datos = {k: v for k, v in datos.items() if k in ("estado", "observacion")}

    if datos.get("estado"):
        garantia.estado = datos["estado"]
    if "observacion" in datos:
        garantia.observacion = datos["observacion"] or ""
    if datos.get("motivo"):
        garantia.motivo = datos["motivo"]
    if "imagen_nombre" in datos:
        garantia.imagenNombre = datos["imagen_nombre"]
    if datos.get("observaciones") is not None:
        garantia.observaciones = json.dumps(datos["observaciones"], ensure_ascii=False)
    if datos.get("bitacora") is not None:
        garantia.bitacora = json.dumps(datos["bitacora"], ensure_ascii=False)

    db.commit()
    return [garantia_json(garantia)]


@router.delete("/{garantia_id}", summary="Eliminar una garantía")
def eliminar_garantia(garantia_id: int, db: Session = Depends(get_db), _=Depends(exigir_staff)):
    garantia = db.get(Garantia, garantia_id)
    if garantia is None:
        raise HTTPException(status_code=404, detail="La garantía no existe.")
    fila = garantia_json(garantia)
    db.delete(garantia)
    db.commit()
    return [fila]
