from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship
from app.infrastructure.database.base import Base



class UnidadVenta(Base):
    __tablename__ = "unidadVentas"

    idUnidadVenta = Column(Integer, primary_key=True, autoincrement=False)
    nombreUnidadMedida = Column(String(45), nullable=False)

    materiales = relationship("Inventario", back_populates="unidad_medida")