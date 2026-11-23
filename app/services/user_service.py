"""
Servicio de usuarios: aplica las reglas de negocio de la gestión de usuarios.

- Evita correos e identificaciones duplicados.
- Protege la contraseña con Argon2 (nunca se guarda ni se devuelve en claro).
- Crea el perfil que corresponde al rol (cliente / proveedor).
- Revoca las sesiones activas al desactivar una cuenta.
"""

from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.domain.enums.user_role import UserRole
from app.domain.rules import usuarios as reglas
from app.models.cliente import Cliente
from app.models.direccion import Direccion
from app.models.proveedor import Proveedor
from app.models.sesion_usuario import SesionUsuario
from app.models.usuario import Usuario
from app.repositories.user_repository import UserRepository
from app.schemas.user import DireccionCreate, UserCreate, UserUpdate


class UserServiceError(Exception):
    pass


class UserNotFoundError(UserServiceError):
    pass


class UserAlreadyExistsError(UserServiceError):
    pass


class UserService:
    @staticmethod
    def create_user(db: Session, data: UserCreate) -> Usuario:
        email = str(data.email).strip().lower()

        if UserRepository.get_by_email(db, email):
            raise UserAlreadyExistsError("Ya existe un usuario registrado con ese correo.")

        # E5: identificación única.
        if data.identificacion is not None:
            reglas.validar_identificacion(data.identificacion)
            if UserRepository.get_by_id(db, data.identificacion):
                raise UserAlreadyExistsError("Ya existe un usuario con esa identificación.")

        try:
            identificacion = data.identificacion or UserRepository.next_identificacion(db)

            datos_direccion = (data.direccion or DireccionCreate()).model_dump()
            direccion = Direccion(**datos_direccion)
            db.add(direccion)
            db.flush()

            usuario = Usuario(
                identificacion=identificacion,
                nombre=data.nombre.strip(),
                apellidos=data.apellidos.strip(),
                correoElectronico=email,
                telefono=(data.telefono or "").strip(),
                contrasena=hash_password(data.password),
                rol_idRol=int(data.rol),
                direccion_idDireccion=direccion.idDireccion,
                activo=True,
            )
            db.add(usuario)
            db.flush()

            if data.rol == UserRole.CLIENTE:
                perfil = data.perfil_cliente.model_dump() if data.perfil_cliente else {}
                db.add(
                    Cliente(
                        carritoActivo=perfil.get("carritoActivo", False),
                        usuario_identificacion=usuario.identificacion,
                    )
                )
            elif data.rol == UserRole.PROVEEDOR:
                perfil = data.perfil_proveedor.model_dump()
                db.add(
                    Proveedor(
                        tipoProducto=perfil["tipoProducto"].strip(),
                        nit=(perfil.get("nit") or "").strip() or None,
                        usuario_identificacion=usuario.identificacion,
                    )
                )

            db.commit()
            db.refresh(usuario)
            return usuario

        except IntegrityError as exc:
            db.rollback()
            raise UserAlreadyExistsError(
                "No fue posible registrar el usuario. "
                "Verifica que el correo o la identificación no estén duplicados."
            ) from exc
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_user(db: Session, identificacion: int) -> Usuario:
        usuario = UserRepository.get_by_id(db, identificacion)
        if usuario is None:
            raise UserNotFoundError("No se encontró el usuario solicitado.")
        return usuario

    @staticmethod
    def list_users(
        db: Session,
        rol: UserRole | None = None,
        activo: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Usuario]:
        return UserRepository.list_users(db, rol=rol, activo=activo, skip=skip, limit=limit)

    @staticmethod
    def update_user(db: Session, identificacion: int, data: UserUpdate) -> Usuario:
        usuario = UserService.get_user(db, identificacion)
        reglas.validar_edicion(usuario.rol_idRol)

        cambios = data.model_dump(exclude_unset=True)

        if cambios.get("email") is not None:
            cambios["email"] = str(cambios["email"]).strip().lower()
            existente = UserRepository.get_by_email(db, cambios["email"])
            if existente is not None and existente.identificacion != usuario.identificacion:
                raise UserAlreadyExistsError("Ese correo electrónico ya está registrado.")

        columnas = {
            "nombre": "nombre",
            "apellidos": "apellidos",
            "email": "correoElectronico",
            "telefono": "telefono",
        }
        for campo, valor in cambios.items():
            if valor is None:  # las columnas no admiten NULL: None = "no cambiar"
                continue
            if isinstance(valor, str):
                valor = valor.strip()
            setattr(usuario, columnas[campo], valor)

        try:
            db.commit()
            db.refresh(usuario)
            return usuario
        except IntegrityError as exc:
            db.rollback()
            raise UserAlreadyExistsError(
                "No fue posible actualizar el usuario. Verifica que el correo no esté duplicado."
            ) from exc
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def change_status(
        db: Session, identificacion: int, activo: bool, id_actor: int
    ) -> Usuario:
        usuario = UserService.get_user(db, identificacion)
        reglas.validar_cambio_estado(
            usuario.rol_idRol, usuario.identificacion, id_actor, activar=activo
        )

        usuario.activo = activo

        # Cuenta desactivada => sus sesiones abiertas dejan de servir.
        if not activo:
            ahora = datetime.now(timezone.utc).replace(tzinfo=None)
            db.execute(
                update(SesionUsuario)
                .where(
                    SesionUsuario.usuario_identificacion == usuario.identificacion,
                    SesionUsuario.activa.is_(True),
                )
                .values(activa=False, fechaRevocacion=ahora)
            )

        try:
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception:
            db.rollback()
            raise

