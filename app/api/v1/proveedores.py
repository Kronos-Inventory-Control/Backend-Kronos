"""Proveedores. Cada proveedor es un usuario con rol PROVEEDOR más su ficha."""

import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.v1.common import (
    a_iso,
    es_staff,
    exigir_staff,
    ordenar,
    siguiente_identificacion,
)
from app.core.security import hash_password
from app.domain.enums.user_role import UserRole
from app.infrastructure.database.session import get_db
from app.models.direccion import Direccion
from app.models.proveedor import Proveedor
from app.models.sesion_usuario import SesionUsuario
from app.models.usuario import Usuario

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])

ORDEN_PROV = {"nombre": Usuario.nombre, "fecha": Usuario.fechaCreacion}


def proveedor_json(p: Proveedor, u: Usuario, d: Direccion) -> dict:
    return {
        "id": p.idProveedor,
        "perfil_id": u.identificacion,
        "nombre": f"{u.nombre} {u.apellidos}".strip(),
        "nit": p.nit,
        "telefono": u.telefono,
        "direccion": d.direccionCompleta,
        "correo": u.correoElectronico,
        "tipo_producto": p.tipoProducto,
        "activo": bool(u.activo),
        "creado_en": a_iso(u.fechaCreacion),
    }


def _consulta():
    return (
        select(Proveedor, Usuario, Direccion)
        .join(Usuario, Usuario.identificacion == Proveedor.usuario_identificacion)
        .join(Direccion, Direccion.idDireccion == Usuario.direccion_idDireccion)
    )


def _cargar(db: Session, proveedor_id: int):
    fila = db.execute(_consulta().where(Proveedor.idProveedor == proveedor_id)).first()
    if fila is None:
        raise HTTPException(status_code=404, detail="El proveedor no existe.")
    return fila


class ProveedorIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=45)
    nit: str | None = Field(default=None, max_length=30)
    telefono: str | None = Field(default=None, max_length=20)
    direccion: str | None = Field(default=None, max_length=200)
    correo: str | None = Field(default=None, max_length=120)
    tipo_producto: str | None = Field(default=None, max_length=45)
    activo: bool = True


class ProveedoresIn(BaseModel):
    filas: list[ProveedorIn] = Field(min_length=1)


class ProveedorPatch(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=45)
    nit: str | None = Field(default=None, max_length=30)
    telefono: str | None = Field(default=None, max_length=20)
    direccion: str | None = Field(default=None, max_length=200)
    correo: str | None = Field(default=None, max_length=120)
    tipo_producto: str | None = Field(default=None, max_length=45)
    activo: bool | None = None


def _correo_ocupado(db: Session, correo: str, excepto: int | None = None) -> bool:
    consulta = select(Usuario.identificacion).where(Usuario.correoElectronico == correo)
    if excepto is not None:
        consulta = consulta.where(Usuario.identificacion != excepto)
    return db.execute(consulta).first() is not None


@router.get("", summary="Lista de proveedores")
def listar_proveedores(
    perfil_id: int | None = None, orden: str | None = None, asc: bool = True,
    db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user),
):
    if es_staff(usuario):
        pass
    elif usuario.rol_idRol == int(UserRole.PROVEEDOR):
        perfil_id = usuario.identificacion  # un proveedor solo ve su propia ficha
    else:
        raise HTTPException(status_code=403, detail="No tienes permiso para esta operación.")

    consulta = _consulta()
    if perfil_id is not None:
        consulta = consulta.where(Usuario.identificacion == perfil_id)
    consulta = ordenar(consulta, ORDEN_PROV, orden, asc, Proveedor.idProveedor)
    return [proveedor_json(*fila) for fila in db.execute(consulta).all()]


@router.post("", summary="Registrar proveedores")
def crear_proveedores(body: ProveedoresIn, db: Session = Depends(get_db), _=Depends(exigir_staff)):
    ids = []
    try:
        for f in body.filas:
            identificacion = siguiente_identificacion(db)
            correo = (f.correo or "").strip().lower() or f"proveedor{identificacion}@sin-correo.local"
            if _correo_ocupado(db, correo):
                raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo.")

            direccion = Direccion(
                barrio="", ciudad="", localidad="", direccionCompleta=(f.direccion or "").strip()
            )
            db.add(direccion)
            db.flush()

            usuario = Usuario(
                identificacion=identificacion,
                nombre=f.nombre.strip(),
                apellidos="",
                correoElectronico=correo,
                telefono=(f.telefono or "").strip(),
                # Contraseña aleatoria: el proveedor entra con «Olvidé mi contraseña».
                contrasena=hash_password(secrets.token_urlsafe(24)),
                rol_idRol=int(UserRole.PROVEEDOR),
                direccion_idDireccion=direccion.idDireccion,
                activo=f.activo,
            )
            db.add(usuario)
            db.flush()

            proveedor = Proveedor(
                tipoProducto=(f.tipo_producto or "").strip(),
                nit=(f.nit or "").strip() or None,
                usuario_identificacion=identificacion,
            )
            db.add(proveedor)
            db.flush()
            ids.append(proveedor.idProveedor)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return [proveedor_json(*_cargar(db, i)) for i in ids]


@router.patch("/{proveedor_id}", summary="Actualizar un proveedor")
def actualizar_proveedor(
    proveedor_id: int, body: ProveedorPatch,
    db: Session = Depends(get_db), actual: Usuario = Depends(get_current_user),
):
    proveedor, usuario, direccion = _cargar(db, proveedor_id)
    es_el_mismo = usuario.identificacion == actual.identificacion
    if not (es_staff(actual) or es_el_mismo):
        raise HTTPException(status_code=403, detail="No tienes permiso para esta operación.")

    datos = body.model_dump(exclude_unset=True)
    if not es_staff(actual):
        datos.pop("activo", None)  # un proveedor no se activa ni desactiva solo

    if datos.get("nombre"):
        usuario.nombre = datos["nombre"].strip()
        usuario.apellidos = ""
    if "nit" in datos:
        proveedor.nit = (datos["nit"] or "").strip() or None
    if "telefono" in datos:
        usuario.telefono = (datos["telefono"] or "").strip()
    if "direccion" in datos:
        direccion.direccionCompleta = (datos["direccion"] or "").strip()
    if datos.get("correo"):
        correo = datos["correo"].strip().lower()
        if _correo_ocupado(db, correo, excepto=usuario.identificacion):
            raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo.")
        usuario.correoElectronico = correo
    if "tipo_producto" in datos:
        proveedor.tipoProducto = (datos["tipo_producto"] or "").strip()
    if "activo" in datos and datos["activo"] is not None:
        usuario.activo = datos["activo"]

    db.commit()
    return [proveedor_json(*_cargar(db, proveedor_id))]


@router.delete("/{proveedor_id}", summary="Eliminar un proveedor")
def eliminar_proveedor(proveedor_id: int, db: Session = Depends(get_db), _=Depends(exigir_staff)):
    proveedor, usuario, direccion = _cargar(db, proveedor_id)
    fila = proveedor_json(proveedor, usuario, direccion)
    try:
        db.execute(delete(SesionUsuario).where(SesionUsuario.usuario_identificacion == usuario.identificacion))
        db.delete(proveedor)
        db.flush()
        db.delete(usuario)
        db.flush()
        db.delete(direccion)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: el proveedor tiene órdenes asociadas. Desactívalo en su lugar.",
        )
    return [fila]
