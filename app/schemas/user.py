"""
Esquemas de usuarios de Kronos Inventory Control.

Definen la información que el backend puede devolver
sin exponer datos privados (nunca incluyen la contraseña ni su hash).
"""

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.domain.enums.user_role import UserRole
from app.domain.exceptions import ReglaDeNegocioError
from app.domain.rules.usuarios import validar_perfiles_para_rol


class DireccionResponse(BaseModel):
    """Dirección del usuario (la devuelve /auth/me)."""

    model_config = ConfigDict(from_attributes=True)

    barrio: str
    ciudad: str
    localidad: str
    direccionCompleta: str


class UserResponse(BaseModel):
    """
    Información pública de un usuario.

    No incluye `contrasena` (hash) ni otros datos privados.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    identificacion: int
    nombre: str
    apellidos: str
    correoElectronico: EmailStr
    telefono: str | None
    rol: UserRole = Field(validation_alias="rol_idRol")
    activo: bool
    fechaCreacion: datetime
    fechaActualizacion: datetime
    direccion: DireccionResponse | None = None


# ---------------------------------------------------------------------------
# Gestión de usuarios (módulo /users, solo SUPER_ADMIN)
# ---------------------------------------------------------------------------
class DireccionCreate(BaseModel):
    """Dirección del usuario (la tabla `usuarios` exige una)."""

    barrio: str = Field(default="", max_length=45)
    ciudad: str = Field(default="Bogotá", max_length=45)
    localidad: str = Field(default="", max_length=45)
    direccionCompleta: str = Field(default="", max_length=200)


class PerfilClienteCreate(BaseModel):
    """Datos adicionales de un cliente (tabla `clientes`)."""

    carritoActivo: bool = False


class PerfilProveedorCreate(BaseModel):
    """Datos adicionales de un proveedor (tabla `proveedores`)."""

    tipoProducto: str = Field(min_length=2, max_length=45)
    nit: str | None = Field(default=None, max_length=30)


class UserCreate(BaseModel):
    """Datos para registrar un usuario."""

    identificacion: int | None = Field(
        default=None,
        gt=0,
        description="Opcional: si se omite, el sistema asigna la siguiente. Debe ser única.",
    )
    nombre: str = Field(min_length=2, max_length=45)
    apellidos: str = Field(min_length=2, max_length=45)
    email: EmailStr
    telefono: str | None = Field(default=None, max_length=20)
    password: str = Field(min_length=12, max_length=128)
    rol: UserRole

    direccion: DireccionCreate | None = None
    perfil_cliente: PerfilClienteCreate | None = None
    perfil_proveedor: PerfilProveedorCreate | None = None

    @field_validator("rol", mode="before")
    @classmethod
    def _rol_por_nombre(cls, valor):
        """Acepta el nombre del rol ("JEFE") además de su número (3)."""
        if isinstance(valor, str) and valor.upper() in UserRole.__members__:
            return UserRole[valor.upper()]
        return valor

    @model_validator(mode="after")
    def _validar_rol_y_perfiles(self):
        # La regla vive en el dominio; aquí solo se traduce a error de validación.
        try:
            validar_perfiles_para_rol(
                self.rol,
                tiene_perfil_cliente=self.perfil_cliente is not None,
                tiene_perfil_proveedor=self.perfil_proveedor is not None,
            )
        except ReglaDeNegocioError as exc:
            raise ValueError(str(exc)) from exc
        return self


class UserUpdate(BaseModel):
    """
    Datos permitidos para actualizar.

    No incluye `rol`: el rol no se cambia con una actualización ordinaria
    (si se envía, se rechaza con 422).
    """

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=2, max_length=45)
    apellidos: str | None = Field(default=None, min_length=2, max_length=45)
    email: EmailStr | None = None
    telefono: str | None = Field(default=None, max_length=20)


class UserStatusUpdate(BaseModel):
    """Cambio de estado de la cuenta."""

    activo: bool
