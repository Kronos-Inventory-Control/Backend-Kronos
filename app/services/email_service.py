"""
Envío de correos reales por SMTP (sin dependencias extra: solo la biblioteca
estándar de Python).

Configuración en el .env:
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_FROM_NAME

Gmail: SMTP_HOST=smtp.gmail.com, SMTP_PORT=587 y como SMTP_PASSWORD una
«contraseña de aplicación» (no la clave normal de la cuenta).
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings
from app.domain.rules.usuarios import (
    CODIGO_VIGENCIA_MINUTOS,
    PROPOSITO_CAMBIAR_CORREO,
    PROPOSITO_RECUPERAR_PASSWORD,
)

logger = logging.getLogger("kronos.correo")

SMTP_TIMEOUT_SEGUNDOS = 15


class CorreoNoEnviadoError(Exception):
    """No se pudo entregar el correo al servidor SMTP."""


def _remitente() -> str:
    direccion = settings.smtp_from or settings.smtp_user
    return formataddr((settings.smtp_from_name, direccion))


def enviar_correo(destino: str, asunto: str, texto: str, html: str | None = None) -> None:
    """Envía un correo. Lanza CorreoNoEnviadoError si el servidor SMTP lo rechaza."""
    if not settings.smtp_host:
        raise CorreoNoEnviadoError("SMTP_HOST no está configurado en el .env.")

    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = _remitente()
    mensaje["To"] = destino
    mensaje.set_content(texto)
    if html:
        mensaje.add_alternative(html, subtype="html")

    contexto = ssl.create_default_context()
    try:
        if settings.smtp_port == 465:
            servidor = smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port,
                timeout=SMTP_TIMEOUT_SEGUNDOS, context=contexto,
            )
        else:
            servidor = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=SMTP_TIMEOUT_SEGUNDOS)
        with servidor:
            if settings.smtp_port != 465:
                servidor.starttls(context=contexto)
            if settings.smtp_user:
                servidor.login(settings.smtp_user, settings.smtp_password)
            servidor.send_message(mensaje)
    except (smtplib.SMTPException, OSError) as error:
        logger.exception("No se pudo enviar el correo a %s", destino)
        raise CorreoNoEnviadoError(str(error)) from error


def _plantilla_html(titulo: str, introduccion: str, codigo: str, pie: str) -> str:
    return f"""\
<!doctype html>
<html lang="es"><body style="margin:0;background:#0b0e14;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0b0e14;padding:32px 12px;">
    <tr><td align="center">
      <table role="presentation" width="480" cellpadding="0" cellspacing="0"
             style="max-width:480px;background:#15171b;border:1px solid #33383f;border-radius:12px;padding:32px;">
        <tr><td style="color:#e8600c;font-size:14px;font-weight:700;letter-spacing:2px;">KRONOS INVENTORY</td></tr>
        <tr><td style="color:#f1f0ec;font-size:22px;font-weight:700;padding:12px 0 8px;">{titulo}</td></tr>
        <tr><td style="color:#aab1bf;font-size:14px;line-height:1.5;">{introduccion}</td></tr>
        <tr><td align="center" style="padding:24px 0;">
          <span style="display:inline-block;background:#0b0e14;border:1px solid #e8600c;border-radius:8px;
                       color:#f1f0ec;font-size:34px;font-weight:700;letter-spacing:10px;padding:14px 22px;">{codigo}</span>
        </td></tr>
        <tr><td style="color:#aab1bf;font-size:13px;line-height:1.5;">
          Este código vence en {CODIGO_VIGENCIA_MINUTOS} minutos y solo sirve una vez.<br>{pie}
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def enviar_codigo(destino: str, codigo: str, proposito: str) -> None:
    """
    Envía el código de 6 dígitos. Sin SMTP configurado y con DEBUG=true el
    código se imprime en la consola del backend (solo desarrollo).
    """
    if proposito == PROPOSITO_RECUPERAR_PASSWORD:
        asunto = f"{codigo} es tu código para recuperar tu contraseña de Kronos"
        titulo = "Recupera tu contraseña"
        introduccion = "Recibimos una solicitud para restablecer la contraseña de tu cuenta. Escribe este código en la pantalla de Kronos:"
        pie = "Si no fuiste tú, ignora este mensaje: tu contraseña no cambiará."
    elif proposito == PROPOSITO_CAMBIAR_CORREO:
        asunto = f"{codigo} es tu código para confirmar tu nuevo correo en Kronos"
        titulo = "Confirma tu nuevo correo"
        introduccion = "Alguien pidió usar este correo en una cuenta de Kronos. Para confirmarlo, escribe este código en la pantalla de Kronos:"
        pie = "Si no fuiste tú, ignora este mensaje: el correo de la cuenta no cambiará."
    else:
        raise ValueError(f"Propósito de código desconocido: {proposito}")

    texto = (
        f"{titulo}\n\n{introduccion}\n\n    {codigo}\n\n"
        f"Este código vence en {CODIGO_VIGENCIA_MINUTOS} minutos y solo sirve una vez.\n{pie}\n"
    )

    if not settings.smtp_host:
        if settings.debug:
            logger.warning("[DESARROLLO] Código %s para %s (%s)", codigo, destino, proposito)
            print(f"\n[Kronos] Código {proposito} para {destino}: {codigo}\n", flush=True)
            return
        raise CorreoNoEnviadoError("SMTP_HOST no está configurado en el .env.")

    enviar_correo(destino, asunto, texto, _plantilla_html(titulo, introduccion, codigo, pie))


def enviar_aviso_cambio_correo(destino_anterior: str, correo_nuevo: str) -> None:
    """Avisa al correo anterior que la cuenta cambió de dirección (seguridad)."""
    if not settings.smtp_host:
        return
    texto = (
        "El correo de tu cuenta de Kronos Inventory fue cambiado a "
        f"{correo_nuevo}.\n\nSi no fuiste tú, comunícate de inmediato con el administrador.\n"
    )
    try:
        enviar_correo(destino_anterior, "El correo de tu cuenta de Kronos fue cambiado", texto)
    except CorreoNoEnviadoError:
        pass  # el aviso es un extra: si falla no deshace el cambio
