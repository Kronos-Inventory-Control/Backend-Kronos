"""
Esquemas de usuarios de Kronos Inventory Control.

Definen la información que el backend puede devolver
sin exponer datos privados (nunca incluyen la contraseña ni su hash).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums.user_role import UserRole


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
