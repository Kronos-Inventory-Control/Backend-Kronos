from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class CodigoVerificacion(Base):
    """
    Código de 6 dígitos enviado por correo para recuperar la contraseña o
    confirmar un cambio de correo. Nunca se guarda el código en claro: solo su
    huella HMAC-SHA256.
    """

    __tablename__ = "codigosVerificacion"
    __table_args__ = (
        Index(
            "ix_codigosVerificacion_usuario_proposito",
            "usuario_identificacion",
            "proposito",
        ),
    )

    idCodigo: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Llave primaria. Identificador autoincremental del código.",
    )

    usuario_identificacion: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuarios.identificacion", name="fk_codigo_usuario1"),
        nullable=False,
        comment="Clave foránea. Usuario al que pertenece el código.",
    )

    proposito: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Para qué se emitió: RECUPERAR_PASSWORD o CAMBIAR_CORREO.",
    )

    correoDestino: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        comment="Correo al que se envió el código. En CAMBIAR_CORREO es el correo nuevo que se va a confirmar.",
    )

    codigoHash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Huella HMAC-SHA256 del código. El código en claro no se almacena.",
    )

    intentos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Intentos fallidos de verificación. Al llegar al máximo el código se invalida.",
    )

    usado: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
        comment="1 si el código ya se usó, se reemplazó por otro o se invalidó.",
    )

    fechaCreacion: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="Fecha y hora (UTC) en que se emitió el código.",
    )

    fechaExpiracion: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Fecha y hora (UTC) en que el código deja de ser válido.",
    )
