from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class UnidadVenta(Base):
    __tablename__ = "unidadVentas"

    idUnidadVenta: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=False,
        comment="Clave primaria. Identificador de la unidad (ej. piezas o unidades).",
    )

    nombreUnidadMedida: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        comment="Nombre de la unidad de medida.",
    )

    materiales = relationship("Inventario", back_populates="unidad_medida")