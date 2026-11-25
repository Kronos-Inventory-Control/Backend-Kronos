"""
Códigos de verificación de 6 dígitos (recuperar contraseña / cambiar correo).

- El código en claro solo existe en el correo enviado; en MySQL se guarda su
  huella HMAC-SHA256 (con la JWT_SECRET_KEY), ligada al usuario y al propósito.
- Las reglas (vigencia, intentos, espera de reenvío) están en
  `app/domain/rules/usuarios.py`.
"""

import hashlib
import hmac
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.v1.common import ahora
from app.core.config import settings
from app.domain.exceptions import CodigoVerificacionError
from app.domain.rules.usuarios import (
    CODIGO_MAX_INTENTOS,
    MENSAJE_CODIGO_INVALIDO,
    calcular_vencimiento,
    formato_codigo_valido,
    generar_codigo,
    validar_codigo_utilizable,
    validar_espera_reenvio,
    validar_proposito_codigo,
)
from app.models.codigo_verificacion import CodigoVerificacion
from app.models.usuario import Usuario


def _huella(usuario_id: int, proposito: str, codigo: str) -> str:
    mensaje = f"{usuario_id}:{proposito}:{codigo}".encode()
    return hmac.new(settings.jwt_secret_key.encode(), mensaje, hashlib.sha256).hexdigest()


def _ultimo_codigo(db: Session, usuario_id: int, proposito: str) -> CodigoVerificacion | None:
    return db.scalars(
        select(CodigoVerificacion)
        .where(
            CodigoVerificacion.usuario_identificacion == usuario_id,
            CodigoVerificacion.proposito == proposito,
        )
        .order_by(CodigoVerificacion.idCodigo.desc())
        .limit(1)
    ).first()


def emitir_codigo(db: Session, usuario: Usuario, proposito: str, correo_destino: str) -> str:
    """
    Crea un código nuevo (invalida los anteriores del mismo propósito) y lo
    devuelve en claro para enviarlo por correo.
    Lanza EsperaReenvioError si se pide otro antes de 60 segundos.
    """
    validar_proposito_codigo(proposito)
    momento = ahora()

    anterior = _ultimo_codigo(db, usuario.identificacion, proposito)
    validar_espera_reenvio(anterior.fechaCreacion if anterior else None, momento)

    db.execute(
        update(CodigoVerificacion)
        .where(
            CodigoVerificacion.usuario_identificacion == usuario.identificacion,
            CodigoVerificacion.proposito == proposito,
            CodigoVerificacion.usado.is_(False),
        )
        .values(usado=True)
    )

    codigo = generar_codigo()
    db.add(
        CodigoVerificacion(
            usuario_identificacion=usuario.identificacion,
            proposito=proposito,
            correoDestino=correo_destino,
            codigoHash=_huella(usuario.identificacion, proposito, codigo),
            intentos=0,
            usado=False,
            fechaCreacion=momento,  # UTC explícito: no depende de la zona horaria de MySQL
            fechaExpiracion=calcular_vencimiento(momento),
        )
    )
    db.commit()
    return codigo


def anular_codigos(db: Session, usuario: Usuario, proposito: str) -> None:
    """Invalida los códigos pendientes (p. ej. si el correo no se pudo enviar)."""
    db.execute(
        update(CodigoVerificacion)
        .where(
            CodigoVerificacion.usuario_identificacion == usuario.identificacion,
            CodigoVerificacion.proposito == proposito,
            CodigoVerificacion.usado.is_(False),
        )
        .values(usado=True, fechaCreacion=ahora() - timedelta(days=1))  # así no bloquea el reintento
    )
    db.commit()


def consumir_codigo(
    db: Session, usuario: Usuario, proposito: str, codigo: str
) -> CodigoVerificacion:
    """
    Verifica el código y lo marca como usado (SIN hacer commit: lo hace quien
    llama junto con su propio cambio). Si es incorrecto suma un intento y, al
    llegar a 5, lo invalida. Lanza CodigoVerificacionError con un mensaje único
    para no revelar si falló por vencido, usado o erróneo.
    """
    validar_proposito_codigo(proposito)
    registro = _ultimo_codigo(db, usuario.identificacion, proposito)
    if registro is None or not formato_codigo_valido(codigo):
        raise CodigoVerificacionError(MENSAJE_CODIGO_INVALIDO)

    validar_codigo_utilizable(
        usado=registro.usado,
        intentos=registro.intentos,
        vencimiento=registro.fechaExpiracion,
        ahora=ahora(),
    )

    esperado = _huella(usuario.identificacion, proposito, codigo)
    if not hmac.compare_digest(esperado, registro.codigoHash):
        registro.intentos += 1
        if registro.intentos >= CODIGO_MAX_INTENTOS:
            registro.usado = True
        db.commit()  # el intento fallido debe quedar guardado
        raise CodigoVerificacionError(MENSAJE_CODIGO_INVALIDO)

    registro.usado = True
    return registro
