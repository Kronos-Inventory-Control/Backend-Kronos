"""
Repositorio de usuarios: consulta y guarda en MySQL.

No contiene reglas de permisos ni validaciones de negocio (eso es del dominio
y del servicio).
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums.user_role import UserRole
from app.models.direccion import Direccion
from app.models.usuario import Usuario

PRIMERA_IDENTIFICACION_AUTOMATICA = 1_000_000


class UserRepository:
    @staticmethod
    def get_by_id(db: Session, identificacion: int) -> Usuario | None:
        return db.scalar(select(Usuario).where(Usuario.identificacion == identificacion))

    @staticmethod
    def get_by_email(db: Session, email: str) -> Usuario | None:
        return db.scalar(select(Usuario).where(Usuario.correoElectronico == email))

    @staticmethod
    def list_users(
        db: Session,
        rol: UserRole | None = None,
        activo: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Usuario]:
        consulta = select(Usuario)
        if rol is not None:
            consulta = consulta.where(Usuario.rol_idRol == int(rol))
        if activo is not None:
            consulta = consulta.where(Usuario.activo.is_(activo))
        consulta = (
            consulta.order_by(Usuario.fechaCreacion.desc(), Usuario.identificacion.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(consulta).all())

    @staticmethod
    def get_direcciones(db: Session, ids_direccion: list[int]) -> dict[int, Direccion]:
        if not ids_direccion:
            return {}
        filas = db.scalars(select(Direccion).where(Direccion.idDireccion.in_(ids_direccion)))
        return {d.idDireccion: d for d in filas}

    @staticmethod
    def next_identificacion(db: Session) -> int:
        """Siguiente identificación para usuarios creados desde la app (bloquea el índice)."""
        maximo = db.execute(select(func.max(Usuario.identificacion)).with_for_update()).scalar()
        return max(int(maximo or 0), PRIMERA_IDENTIFICACION_AUTOMATICA - 1) + 1
