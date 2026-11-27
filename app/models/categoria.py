from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class Categoria(Base):
    __tablename__ = "categorias"

    idCategoria: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=False,
        comment="Clave primaria. Identificador de la categoría del producto.",
    )

    nombreCategoria: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        comment="Nombre de la categoría.",
    )

    descripcion: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Descripción opcional de la categoría (la usa la pantalla de stock).",
    )
    icono: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Nombre del icono con el que se muestra la categoría en el frontend.",
    )
