from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship

from app.infrastructure.database.base import Base


class Marca(Base):
    __tablename__ = "marcas"

    idMarca = Column(Integer, primary_key=True, autoincrement=True)
    nombreMarca = Column(String(45), nullable=False)

    materiales = relationship("Inventario", back_populates="marca")
