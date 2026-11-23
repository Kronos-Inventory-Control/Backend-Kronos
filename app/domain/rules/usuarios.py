"""E. Usuarios y roles."""

import enum

from app.domain.enums.user_role import UserRole
from app.domain.exceptions import PermisoDenegadoError, UsuarioInvalidoError


class Operacion(enum.Enum):
    GESTIONAR_USUARIOS = "gestionar_usuarios"  # exclusiva de administración
    GESTIONAR_INVENTARIO = "gestionar_inventario"
    REGISTRAR_MOVIMIENTOS = "registrar_movimientos"
    GESTIONAR_PROVEEDORES = "gestionar_proveedores"
    GESTIONAR_ORDENES_COMPRA = "gestionar_ordenes_compra"
    GESTIONAR_GARANTIAS = "gestionar_garantias"
    GENERAR_REPORTES = "generar_reportes"
    COMPRAR = "comprar"
    SOLICITAR_GARANTIA = "solicitar_garantia"
    GESTIONAR_ORDENES_PROPIAS = "gestionar_ordenes_propias"
    EDITAR_PERFIL_PROPIO = "editar_perfil_propio"


_OPERACIONES_STAFF = frozenset(
    {
        Operacion.GESTIONAR_INVENTARIO,
        Operacion.REGISTRAR_MOVIMIENTOS,
        Operacion.GESTIONAR_PROVEEDORES,
        Operacion.GESTIONAR_ORDENES_COMPRA,
        Operacion.GESTIONAR_GARANTIAS,
        Operacion.GENERAR_REPORTES,
        Operacion.EDITAR_PERFIL_PROPIO,
    }
)

# E2: los roles determinan las operaciones permitidas.
PERMISOS: dict[UserRole, frozenset[Operacion]] = {
    UserRole.CLIENTE: frozenset(
        {Operacion.COMPRAR, Operacion.SOLICITAR_GARANTIA, Operacion.EDITAR_PERFIL_PROPIO}
    ),
    UserRole.PROVEEDOR: frozenset(
        {Operacion.GESTIONAR_ORDENES_PROPIAS, Operacion.EDITAR_PERFIL_PROPIO}
    ),
    UserRole.EMPLEADO: _OPERACIONES_STAFF,
    UserRole.JEFE: _OPERACIONES_STAFF,
    UserRole.SUPER_ADMIN: _OPERACIONES_STAFF | {Operacion.GESTIONAR_USUARIOS},
}


def validar_rol(valor: int) -> UserRole:
    """E1: cada usuario debe tener un rol válido."""
    try:
        return UserRole(valor)
    except ValueError:
        raise UsuarioInvalidoError(f"El rol {valor} no es válido.") from None


def puede_ejecutar(rol: int | UserRole, operacion: Operacion) -> bool:
    return operacion in PERMISOS[validar_rol(int(rol))]


def exigir_permiso(rol: int | UserRole, operacion: Operacion) -> None:
    """E2 + E3: p. ej. un cliente no ejecuta operaciones exclusivas de administración."""
    if not puede_ejecutar(rol, operacion):
        raise PermisoDenegadoError("No tienes permiso para esta operación.")


def proveedor_gestiona_orden(proveedor_id_usuario: int | None, proveedor_id_orden: int) -> bool:
    """E4: un proveedor solo gestiona las órdenes que le corresponden."""
    return proveedor_id_usuario is not None and proveedor_id_usuario == proveedor_id_orden


def validar_identificacion(identificacion: int | None) -> None:
    """E5: identificación válida (la unicidad la garantiza la base de datos / el servicio)."""
    if identificacion is None or identificacion <= 0:
        raise UsuarioInvalidoError("La identificación debe ser un número positivo.")


def validar_perfiles_para_rol(
    rol: UserRole, tiene_perfil_cliente: bool, tiene_perfil_proveedor: bool
) -> None:
    """Al crear un usuario: rol creable y perfil coherente con el rol."""
    if rol == UserRole.SUPER_ADMIN:
        raise UsuarioInvalidoError("El SUPER_ADMIN no se puede crear desde este módulo.")
    if rol == UserRole.PROVEEDOR:
        if not tiene_perfil_proveedor:
            raise UsuarioInvalidoError("El proveedor debe tener su perfil de proveedor.")
        if tiene_perfil_cliente:
            raise UsuarioInvalidoError("Un proveedor no puede tener perfil de cliente.")
    elif rol == UserRole.CLIENTE:
        if tiene_perfil_proveedor:
            raise UsuarioInvalidoError("Un cliente no puede tener perfil de proveedor.")
    else:  # JEFE, EMPLEADO
        if tiene_perfil_cliente or tiene_perfil_proveedor:
            raise UsuarioInvalidoError("Un jefe o empleado no lleva perfil de cliente ni de proveedor.")


def validar_edicion(rol_objetivo: int | UserRole) -> None:
    if validar_rol(int(rol_objetivo)) == UserRole.SUPER_ADMIN:
        raise UsuarioInvalidoError("No se puede modificar el SUPER_ADMIN desde este módulo.")


def validar_cambio_estado(
    rol_objetivo: int | UserRole, id_objetivo: int, id_actor: int, activar: bool
) -> None:
    if validar_rol(int(rol_objetivo)) == UserRole.SUPER_ADMIN:
        raise UsuarioInvalidoError("No se puede cambiar el estado del SUPER_ADMIN.")
    if id_objetivo == id_actor and not activar:
        raise UsuarioInvalidoError("No puedes desactivar tu propia cuenta.")
