from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class SesionUsuario(Base):
    """Sesión iniciada por un usuario. Cada JWT emitido tiene un `jti` único aquí."""

    __tablename__ = "sesionesUsuario"
    __table_args__ = (
        Index("ix_sesionesUsuario_usuario_identificacion", "usuario_identificacion"),
    )

    idSesion: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Llave primaria. Identificador autoincremental de la sesión.",
    )

    usuario_identificacion: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuarios.identificacion", name="fk_sesion_usuario1"),
        nullable=False,
        comment="Clave foránea. Usuario dueño de la sesión.",
    )

    jti: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        comment="Identificador único (UUID) del JWT. Permite revocar la sesión individualmente.",
    )

    ultimaActividad: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Última actividad registrada (UTC). Se usa para el límite de inactividad.",
    )

    fechaExpiracion: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Vencimiento absoluto de la sesión (UTC).",
    )

    activa: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
        comment="1 si la sesión sigue vigente; 0 si fue cerrada o venció.",
    )

    fechaRevocacion: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Fecha y hora (UTC) en que se cerró o invalidó la sesión.",
    )

    direccionIp: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Dirección IP desde la que se inició sesión.",
    )

    userAgent: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Navegador o cliente desde el que se inició sesión.",
    )

    fechaCreacion: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="Fecha y hora en que se creó la sesión.",
    )
