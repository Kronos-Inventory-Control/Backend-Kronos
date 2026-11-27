"""
Cuenta del usuario: registro de clientes, cambio de contraseña y de correo,
y recuperación de contraseña.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.v1.common import ahora, obtener_o_crear_cliente, siguiente_identificacion
from app.core.config import settings
from app.core.security import MIN_PASSWORD_LENGTH, hash_password, verify_password
from app.domain.enums.user_role import UserRole
from app.domain.exceptions import CodigoVerificacionError, EsperaReenvioError
from app.domain.rules.usuarios import (
    CODIGO_VIGENCIA_MINUTOS,
    MENSAJE_CODIGO_INVALIDO,
    PROPOSITO_CAMBIAR_CORREO,
    PROPOSITO_RECUPERAR_PASSWORD,
    validar_cambio_correo,
)
from app.infrastructure.database.session import get_db
from app.models.direccion import Direccion
from app.models.sesion_usuario import SesionUsuario
from app.models.usuario import Usuario
from app.services.email_service import (
    CorreoNoEnviadoError,
    enviar_aviso_cambio_correo,
    enviar_codigo,
)
from app.services.limitador import LimitadorIntentos
from app.services.verificacion_service import anular_codigos, consumir_codigo, emitir_codigo

router = APIRouter(prefix="/auth", tags=["Cuenta"])
logger = logging.getLogger("kronos.cuenta")

PROPOSITO_RESET = "password-reset"

limitador_credenciales = LimitadorIntentos()
# Hash de relleno: así tarda igual tanto si la cédula existe como si no.
_HASH_RELLENO = hash_password("relleno-para-igualar-tiempos")
MENSAJE_CREDENCIALES = "La cédula o la contraseña no son correctas."


class RegistroIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=45)
    apellido: str = Field(min_length=1, max_length=45)
    telefono: str | None = Field(default=None, max_length=20)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    localidad: str | None = Field(default=None, max_length=45)
    barrio: str | None = Field(default=None, max_length=45)
    direccion: str | None = Field(default=None, max_length=200)


class PerfilIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=45)
    apellido: str | None = Field(default=None, max_length=45)
    telefono: str | None = Field(default=None, max_length=20)
    direccion: str | None = Field(default=None, max_length=200)
    localidad: str | None = Field(default=None, max_length=45)
    barrio: str | None = Field(default=None, max_length=45)


class CambioPasswordIn(BaseModel):
    nueva: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)


class CambioCorreoIn(BaseModel):
    identificacion: int = Field(gt=0)  # cédula: así no hace falta recordar el correo viejo
    password: str = Field(min_length=1, max_length=128)  # contraseña actual
    correo: EmailStr  # correo nuevo


class ConfirmarCorreoIn(BaseModel):
    identificacion: int = Field(gt=0)
    codigo: str = Field(pattern=r"^\d{6}$")


class OlvidoIn(BaseModel):
    correo: EmailStr


class VerificarCodigoIn(BaseModel):
    correo: EmailStr
    codigo: str = Field(pattern=r"^\d{6}$")


class ResetIn(BaseModel):
    token: str
    nueva: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)


@router.post("/register", status_code=status.HTTP_201_CREATED, summary="Registro de clientes")
def registrar_cliente(body: RegistroIn, db: Session = Depends(get_db)):
    correo = body.email.lower()
    if db.execute(select(Usuario.identificacion).where(Usuario.correoElectronico == correo)).first():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo.")

    try:
        direccion = Direccion(
            barrio=(body.barrio or "").strip(),
            ciudad="Bogotá",
            localidad=(body.localidad or "").strip(),
            direccionCompleta=(body.direccion or "").strip(),
        )
        db.add(direccion)
        db.flush()

        usuario = Usuario(
            identificacion=siguiente_identificacion(db),
            nombre=body.nombre.strip(),
            apellidos=body.apellido.strip(),
            correoElectronico=correo,
            telefono=(body.telefono or "").strip(),
            contrasena=hash_password(body.password),
            rol_idRol=int(UserRole.CLIENTE),
            direccion_idDireccion=direccion.idDireccion,
            activo=True,
        )
        db.add(usuario)
        db.flush()
        obtener_o_crear_cliente(db, usuario)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"mensaje": "Cuenta creada correctamente."}


@router.patch("/me", summary="Editar mi perfil")
def editar_perfil(
    body: PerfilIn, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user),
):
    datos = body.model_dump(exclude_unset=True)
    if datos.get("nombre"):
        usuario.nombre = datos["nombre"].strip()
    if "apellido" in datos:
        usuario.apellidos = (datos["apellido"] or "").strip()
    if "telefono" in datos:
        usuario.telefono = (datos["telefono"] or "").strip()

    direccion = db.get(Direccion, usuario.direccion_idDireccion)
    if direccion is not None:
        if "direccion" in datos:
            direccion.direccionCompleta = (datos["direccion"] or "").strip()
        if "localidad" in datos:
            direccion.localidad = (datos["localidad"] or "").strip()
        if "barrio" in datos:
            direccion.barrio = (datos["barrio"] or "").strip()
    db.commit()
    return {"mensaje": "Perfil actualizado."}


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT, summary="Cambiar contraseña")
def cambiar_password(
    body: CambioPasswordIn, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user),
):
    usuario.contrasena = hash_password(body.nueva)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _correo_ocupado(db: Session, correo: str, excepto_id: int) -> bool:
    return db.execute(
        select(Usuario.identificacion).where(
            Usuario.correoElectronico == correo, Usuario.identificacion != excepto_id
        )
    ).first() is not None


# ------------------------------------------------------------ cambiar correo
@router.post("/change-email", summary="Paso 1: pedir el cambio de correo (envía un código al correo nuevo)")
def solicitar_cambio_correo(
    body: CambioCorreoIn, request: Request, db: Session = Depends(get_db),
):
    """No requiere sesión: la persona demuestra quién es con su cédula y su contraseña."""
    ip = request.client.host if request.client else "desconocida"
    claves = (f"correo:id:{body.identificacion}", f"correo:ip:{ip}")
    if limitador_credenciales.bloqueado(*claves):
        raise HTTPException(status_code=429, detail="Demasiados intentos. Espera 15 minutos e inténtalo de nuevo.")

    usuario = db.get(Usuario, body.identificacion)
    hash_real = usuario.contrasena if usuario is not None else _HASH_RELLENO
    clave_ok = verify_password(body.password, hash_real)
    if usuario is None or not usuario.activo or not clave_ok:
        limitador_credenciales.registrar_fallo(*claves)
        raise HTTPException(status_code=400, detail=MENSAJE_CREDENCIALES)
    limitador_credenciales.limpiar(*claves)

    correo = body.correo.lower()
    validar_cambio_correo(usuario.correoElectronico, correo)
    if _correo_ocupado(db, correo, usuario.identificacion):
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo.")

    try:
        codigo = emitir_codigo(db, usuario, PROPOSITO_CAMBIAR_CORREO, correo)
    except EsperaReenvioError as error:
        raise HTTPException(status_code=429, detail=str(error))

    try:
        enviar_codigo(correo, codigo, PROPOSITO_CAMBIAR_CORREO)
    except CorreoNoEnviadoError:
        anular_codigos(db, usuario, PROPOSITO_CAMBIAR_CORREO)
        raise HTTPException(
            status_code=502,
            detail="No pudimos enviar el correo. Verifica la dirección e inténtalo de nuevo.",
        )
    return {"correo": correo, "expira_en_minutos": CODIGO_VIGENCIA_MINUTOS}


@router.post("/confirm-email", summary="Paso 2: confirmar el cambio de correo con el código")
def confirmar_cambio_correo(
    body: ConfirmarCorreoIn, tareas: BackgroundTasks, db: Session = Depends(get_db),
):
    invalido = HTTPException(status_code=400, detail=MENSAJE_CODIGO_INVALIDO)
    usuario = db.get(Usuario, body.identificacion)
    if usuario is None or not usuario.activo:
        raise invalido

    try:
        registro = consumir_codigo(db, usuario, PROPOSITO_CAMBIAR_CORREO, body.codigo)
    except CodigoVerificacionError:
        raise invalido

    nuevo = registro.correoDestino
    if _correo_ocupado(db, nuevo, usuario.identificacion):
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo.")

    anterior = usuario.correoElectronico
    usuario.correoElectronico = nuevo
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo.")

    tareas.add_task(enviar_aviso_cambio_correo, anterior, nuevo)
    return {"correo": nuevo}


# ------------------------------------------------------ recuperar contraseña
def _huella(usuario: Usuario) -> str:
    """Huella de la contraseña actual: el token de restablecimiento deja de servir cuando se usa."""
    return hashlib.sha256(usuario.contrasena.encode()).hexdigest()[:16]


def _enviar_codigo_recuperacion(correo: str, codigo: str) -> None:
    try:
        enviar_codigo(correo, codigo, PROPOSITO_RECUPERAR_PASSWORD)
    except CorreoNoEnviadoError:
        logger.error("No se pudo enviar el código de recuperación a %s", correo)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT, summary="Paso 1: enviar código de recuperación")
def olvide_contrasena(body: OlvidoIn, tareas: BackgroundTasks, db: Session = Depends(get_db)):
    usuario = db.execute(
        select(Usuario).where(Usuario.correoElectronico == body.correo.lower(), Usuario.activo.is_(True))
    ).scalars().first()
    if usuario is not None:
        try:
            codigo = emitir_codigo(db, usuario, PROPOSITO_RECUPERAR_PASSWORD, usuario.correoElectronico)
            tareas.add_task(_enviar_codigo_recuperacion, usuario.correoElectronico, codigo)
        except EsperaReenvioError:
            pass  # ya hay un código reciente; la respuesta no cambia
    # Siempre 204: no se revela si el correo está registrado.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/verify-reset-code", summary="Paso 2: verificar el código y recibir el permiso para cambiar la contraseña")
def verificar_codigo_recuperacion(body: VerificarCodigoIn, db: Session = Depends(get_db)):
    invalido = HTTPException(status_code=400, detail=MENSAJE_CODIGO_INVALIDO)
    usuario = db.execute(
        select(Usuario).where(Usuario.correoElectronico == body.correo.lower(), Usuario.activo.is_(True))
    ).scalars().first()
    if usuario is None:
        raise invalido  # mismo mensaje que un código erróneo

    try:
        consumir_codigo(db, usuario, PROPOSITO_RECUPERAR_PASSWORD, body.codigo)
    except CodigoVerificacionError:
        raise invalido
    db.commit()

    ahora_utc = datetime.now(timezone.utc)
    vigencia = timedelta(minutes=settings.reset_token_expire_minutes)
    token = jwt.encode(
        {
            "sub": str(usuario.identificacion),
            "purpose": PROPOSITO_RESET,
            "pwd": _huella(usuario),
            "iat": ahora_utc,
            "exp": ahora_utc + vigencia,
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return {"reset_token": token, "expires_in": int(vigencia.total_seconds())}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT, summary="Paso 3: crear la nueva contraseña")
def restablecer_contrasena(body: ResetIn, db: Session = Depends(get_db)):
    invalido = HTTPException(
        status_code=400, detail="La verificación venció. Solicita un código nuevo."
    )
    try:
        datos = jwt.decode(
            body.token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "purpose", "pwd"]},
        )
        if datos["purpose"] != PROPOSITO_RESET:
            raise invalido
        usuario = db.get(Usuario, int(datos["sub"]))
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise invalido

    if usuario is None or not usuario.activo or datos["pwd"] != _huella(usuario):
        raise invalido

    usuario.contrasena = hash_password(body.nueva)
    # Cierra todas las sesiones abiertas de ese usuario.
    db.execute(
        update(SesionUsuario)
        .where(SesionUsuario.usuario_identificacion == usuario.identificacion,
               SesionUsuario.activa.is_(True))
        .values(activa=False, fechaRevocacion=ahora())
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
