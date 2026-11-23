from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class ReporteGenerado(Base):
    """Historial de reportes que el jefe genera desde el panel."""

    __tablename__ = "reportesGenerados"

    idReporte: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
        comment="Identificador único del reporte generado.",
    )
    tipo: Mapped[str] = mapped_column(String(80), nullable=False, comment="Tipo de reporte.")
    categoria: Mapped[str | None] = mapped_column(
        String(80), nullable=True, comment="Categoría o formato con el que se generó.",
    )
    cantidad: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Cantidad de registros incluidos.",
    )
    filtros: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Filtros usados (JSON).",
    )
    valorTotal: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True, comment="Valor total del reporte, si aplica.",
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(),
        comment="Fecha y hora de generación.",
    )
