from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship
from app.infrastructure.database.base import Base


class Categoria(Base):
    __tablename__ = "categorias"

    idCategoria = Column(Integer, primary_key=True, autoincrement=False)
    nombreCategoria = Column(String(45), nullable=False)

    materiales = relationship("Inventario", back_populates="categoria")