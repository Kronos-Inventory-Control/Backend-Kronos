"""Gestión de usuarios (solo SUPER_ADMIN)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.domain.enums.user_role import UserRole
from app.domain.rules.usuarios import Operacion, exigir_permiso
from app.infrastructure.database.session import get_db
from app.models.usuario import Usuario
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    DireccionResponse,
    UserCreate,
    UserResponse,
    UserStatusUpdate,
    UserUpdate,
)
from app.services.user_service import (
    UserAlreadyExistsError,
    UserNotFoundError,
    UserService,
    UserServiceError,
)

router = APIRouter(prefix="/users", tags=["Gestión de usuarios"])


def require_super_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """E2/E3: solo quien tenga el permiso GESTIONAR_USUARIOS (el SUPER_ADMIN)."""
    exigir_permiso(current_user.rol_idRol, Operacion.GESTIONAR_USUARIOS)
    return current_user


def _a_respuestas(db: Session, usuarios: list[Usuario]) -> list[UserResponse]:
    direcciones = UserRepository.get_direcciones(db, [u.direccion_idDireccion for u in usuarios])
    respuestas = []
    for u in usuarios:
        r = UserResponse.model_validate(u)
        d = direcciones.get(u.direccion_idDireccion)
        if d is not None:
            r.direccion = DireccionResponse.model_validate(d)
        respuestas.append(r)
    return respuestas


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             summary="Crear usuario")
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_super_admin),
):
    try:
        return _a_respuestas(db, [UserService.create_user(db, data)])[0]
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("", response_model=list[UserResponse], summary="Listar usuarios")
def list_users(
    rol: UserRole | None = Query(default=None),
    activo: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_super_admin),
):
    usuarios = UserService.list_users(db, rol=rol, activo=activo, skip=skip, limit=limit)
    return _a_respuestas(db, usuarios)


@router.get("/{identificacion}", response_model=UserResponse, summary="Consultar usuario")
def get_user(
    identificacion: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_super_admin),
):
    try:
        return _a_respuestas(db, [UserService.get_user(db, identificacion)])[0]
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/{identificacion}", response_model=UserResponse, summary="Actualizar datos")
def update_user(
    identificacion: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_super_admin),
):
    try:
        return _a_respuestas(db, [UserService.update_user(db, identificacion, data)])[0]
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except UserServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{identificacion}/status", response_model=UserResponse,
              summary="Activar o desactivar")
def change_user_status(
    identificacion: int,
    data: UserStatusUpdate,
    db: Session = Depends(get_db),
    actual: Usuario = Depends(require_super_admin),
):
    try:
        usuario = UserService.change_status(
            db, identificacion, activo=data.activo, id_actor=actual.identificacion
        )
        return _a_respuestas(db, [usuario])[0]
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UserServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
