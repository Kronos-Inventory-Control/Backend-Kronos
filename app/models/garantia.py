from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class Garantia(Base):
    __tablename__ = "garantias"

    idGarantia: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Llave primaria. Código numérico único para identificar cada tipo de póliza o término de garantía en el sistema.",
    )

    fechaInicio: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Fecha a partir de la cual empieza a regir la garantía (usualmente la fecha de compra o fabricación).",
    )

    fechaFin: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Fecha límite de vencimiento de la cobertura de la garantía.",
    )

    estado: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        comment="Estado de la garantía (ej. Activa, Vencida, En Reclamación).",
    )

    observacion: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Términos, condiciones especiales o notas sobre lo que cubre o no cubre la garantía.",
    )

    motivo: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Razón por la cual el cliente solicita hacer efectiva la garantía.",
    )

    tipoFalla: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        comment="Tipo de daño o defecto presentado por el producto.",
    )

    evidenciaImg: Mapped[bytes | None] = mapped_column(
        MEDIUMBLOB,
        nullable=True,
        comment="Imagen que sirve como evidencia del daño o falla reportada.",
    )

    detalleventa_idDetalleVenta: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("detalleVentas.idDetalleVenta", name="fk_garantia_detalleventa1"),
        nullable=True,
        comment="Clave foránea que relaciona la garantía con el artículo específico registrado en el detalle de la venta.",
    )

    ordenRef: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="Referencia de la orden (oc-<id> orden a proveedor, dv-<id> pedido de cliente).",
    )
    numeroOrden: Mapped[str | None] = mapped_column(
        String(60), nullable=True, comment="Código de la orden que se muestra al usuario.",
    )
    clienteId: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Identificación del cliente que radicó la solicitud.",
    )
    clienteNombre: Mapped[str | None] = mapped_column(
        String(120), nullable=True, comment="Nombre del cliente o de quien radica la solicitud.",
    )
    correo: Mapped[str | None] = mapped_column(
        String(120), nullable=True, comment="Correo de contacto de la solicitud.",
    )
    producto: Mapped[str | None] = mapped_column(
        String(120), nullable=True, comment="Nombre del producto sobre el que se reclama.",
    )
    imagenNombre: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Nombre del archivo de evidencia que adjuntó el cliente.",
    )
    observaciones: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Historial de observaciones (JSON).",
    )
    bitacora: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Bitácora de acciones de la solicitud (JSON).",
    )
