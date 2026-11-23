"""
Cuenta del usuario: registro de clientes, cambio de contraseña y de correo,
y recuperación de contraseña.
"""

import hashlib
import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.v1.common import ahora, obtener_o_crear_cliente, siguiente_identificacion
from app.core.config import settings
from app.core.security import hash_password
from app.domain.enums.user_role import UserRole
from app.infrastructure.database.session import get_db
from app.models.direccion import Direccion
from app.models.sesion_usuario import SesionUsuario
from app.models.usuario import Usuario

router = APIRouter(prefix="/auth", tags=["Cuenta"])
logger = logging.getLogger("kronos.cuenta")

PROPOSITO_RESET = "password-reset"


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
    nueva: str = Field(min_length=8, max_length=128)


class CambioCorreoIn(BaseModel):
    correo: EmailStr


class OlvidoIn(BaseModel):
    correo: EmailStr


class ResetIn(BaseModel):
    token: str
    nueva: str = Field(min_length=8, max_length=128)


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


@router.post("/change-email", summary="Cambiar el correo de la cuenta")
def cambiar_correo(
    body: CambioCorreoIn, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user),
):
    correo = body.correo.lower()
    ocupado = db.execute(
        select(Usuario.identificacion).where(
            Usuario.correoElectronico == correo, Usuario.identificacion != usuario.identificacion
        )
    ).first()
    if ocupado:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo.")
    usuario.correoElectronico = correo
    db.commit()
    return {"correo": correo}


# ------------------------------------------------------ recuperar contraseña
def _huella(usuario: Usuario) -> str:
    """Huella de la contraseña actual: el enlace deja de servir cuando se usa."""
    return hashlib.sha256(usuario.contrasena.encode()).hexdigest()[:16]


def _enviar_enlace(correo: str, enlace: str) -> None:
    if not settings.smtp_host:
        # Sin servidor de correo (desarrollo): el enlace se muestra en la consola.
        logger.warning("Enlace de recuperación para %s: %s", correo, enlace)
        print(f"\n[Kronos] Enlace de recuperación para {correo}:\n{enlace}\n", flush=True)
        return
    mensaje = EmailMessage()
    mensaje["Subject"] = "Recupera tu contraseña de Kronos"
    mensaje["From"] = settings.smtp_from or settings.smtp_user
    mensaje["To"] = correo
    mensaje.set_content(
        f"Hola,\n\nUsa este enlace para crear una nueva contraseña "
        f"(vence en {settings.reset_token_expire_minutes} minutos):\n\n{enlace}\n\n"
        "Si no lo solicitaste, ignora este mensaje."
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as servidor:
            servidor.starttls()
            if settings.smtp_user:
                servidor.login(settings.smtp_user, settings.smtp_password)
            servidor.send_message(mensaje)
    except Exception:  # no se le revela al usuario si el correo existe o no
        logger.exception("No se pudo enviar el correo de recuperación")


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT, summary="Solicitar recuperación")
def olvide_contrasena(body: OlvidoIn, tareas: BackgroundTasks, db: Session = Depends(get_db)):
    usuario = db.execute(
        select(Usuario).where(Usuario.correoElectronico == body.correo.lower(), Usuario.activo.is_(True))
    ).scalars().first()
    if usuario is not None:
        ahora_utc = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": str(usuario.identificacion),
                "purpose": PROPOSITO_RESET,
                "pwd": _huella(usuario),
                "iat": ahora_utc,
                "exp": ahora_utc + timedelta(minutes=settings.reset_token_expire_minutes),
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        enlace = f"{settings.frontend_url.rstrip('/')}/cambiar-contrasena?token={token}"
        tareas.add_task(_enviar_enlace, usuario.correoElectronico, enlace)
    # Siempre 204: no se revela si el correo está registrado.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT, summary="Crear nueva contraseña")
def restablecer_contrasena(body: ResetIn, db: Session = Depends(get_db)):
    invalido = HTTPException(
        status_code=400, detail="El enlace no es válido o ya venció. Solicita uno nuevo."
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
