"""
Dependencias de autenticación y autorización de Kronos Inventory Control.

Comprueba:
- Firma y vencimiento del JWT.
- Existencia de la sesión en MySQL.
- Revocación de la sesión.
- Estado del usuario.
- Inactividad máxima de 30 minutos.
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.database.session import get_db
from app.models.sesion_usuario import SesionUsuario
from app.models.usuario import Usuario

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autorizado. Inicia sesión nuevamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Comprobar que exista el encabezado Authorization.
    if credentials is None:
        raise unauthorized

    token = credentials.credentials

    try:
        # 2. Verificar la firma y el vencimiento del JWT.
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "jti", "iat", "exp"]},
        )

        user_id = int(payload["sub"])
        jti = payload["jti"]

    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
        raise unauthorized

    # 3. Buscar la sesión y su usuario.
    result = db.execute(
        select(SesionUsuario, Usuario)
        .join(Usuario, Usuario.identificacion == SesionUsuario.usuario_identificacion)
        .where(
            SesionUsuario.jti == jti,
            SesionUsuario.usuario_identificacion == user_id,
        )
    ).first()

    if result is None:
        raise unauthorized

    session_record, user = result

    # 4. Comprobar que la sesión siga activa.
    if not session_record.activa or session_record.fechaRevocacion:
        raise unauthorized

    # 5. Comprobar que el usuario siga activo.
    if not user.activo:
        raise unauthorized

    # 6. Trabajar con fechas UTC sin zona horaria,
    # porque nuestras columnas MySQL son DateTime sin timezone.
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 7. Comprobar vencimiento absoluto.
    if now >= session_record.fechaExpiracion:
        session_record.activa = False
        session_record.fechaRevocacion = now
        db.commit()
        raise unauthorized

    # 8. Comprobar inactividad.
    inactivity_limit = timedelta(minutes=settings.session_inactivity_minutes)

    if now - session_record.ultimaActividad >= inactivity_limit:
        session_record.activa = False
        session_record.fechaRevocacion = now
        db.commit()
        raise unauthorized

    # 9. Actualizar actividad como máximo cada 5 minutos.
    if now - session_record.ultimaActividad >= timedelta(minutes=5):
        session_record.ultimaActividad = now
        db.commit()

    return user
