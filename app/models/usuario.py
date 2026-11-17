from datetime import datetime

from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        UniqueConstraint("correoElectronico", name="uq_usuarios_correoElectronico"),
        # Solo puede existir un SUPER_ADMIN (rol 5): la columna generada vale 1
        # para ese rol y NULL para los demás; MySQL permite varios NULL pero un solo 1.
        Index("uq_usuarios_super_admin_slot", "super_admin_slot", unique=True),
    )

    identificacion: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=False,
        comment="Llave primaria. Código numérico único para identificar a cada usuario del sistema.",
    )

    nombre: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        comment="Campo de texto. Almacena el primer o segundo nombre de la persona.",
    )

    apellidos: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        comment="Campo de texto. Guarda los apellidos del usuario.",
    )

    correoElectronico: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        comment="Campo de texto. Registra el email para notificaciones e inicio de sesión.",
    )

    telefono: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Número de teléfono o celular de contacto.",
    )

    contrasena: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Campo de texto. Guarda la clave encriptada para el acceso seguro al sistema.",
    )

    rol_idRol: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("roles.idRol", name="fk_usuario_rol1"),
        nullable=False,
        comment="Campo que referencia el identificador del rol asignado al usuario, permitiendo relacionar la tabla Usuario con la tabla Rol.",
    )

    direccion_idDireccion: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("direcciones.idDireccion", name="fk_usuario_direccion1"),
        nullable=False,
        comment="Clave foránea que vincula al usuario con su dirección residencial o comercial.",
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
        comment="Indica si el usuario puede iniciar sesión (1) o está desactivado (0).",
    )

    fechaCreacion: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="Fecha y hora en que se registró el usuario.",
    )

    fechaActualizacion: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Fecha y hora de la última modificación del usuario.",
    )

    super_admin_slot: Mapped[int | None] = mapped_column(
        Integer,
        Computed("CASE WHEN rol_idRol = 5 THEN 1 ELSE NULL END", persisted=True),
        nullable=True,
        comment="Columna generada. Vale 1 solo para el SUPER_ADMIN y, con índice único, garantiza que exista uno solo.",
    )
