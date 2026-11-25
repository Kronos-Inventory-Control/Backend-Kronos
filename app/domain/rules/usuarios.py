"""E. Usuarios y roles."""

import enum
import re
import secrets
import string
from datetime import datetime, timedelta

from app.domain.enums.user_role import UserRole
from app.domain.exceptions import (
    CodigoVerificacionError,
    EsperaReenvioError,
    PermisoDenegadoError,
    UsuarioInvalidoError,
)


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


# --- E6-E8: códigos de verificación por correo -----------------------------
PROPOSITO_RECUPERAR_PASSWORD = "RECUPERAR_PASSWORD"
PROPOSITO_CAMBIAR_CORREO = "CAMBIAR_CORREO"
PROPOSITOS_CODIGO = frozenset({PROPOSITO_RECUPERAR_PASSWORD, PROPOSITO_CAMBIAR_CORREO})

CODIGO_LONGITUD = 6
CODIGO_VIGENCIA_MINUTOS = 10
CODIGO_MAX_INTENTOS = 5
CODIGO_ESPERA_REENVIO_SEGUNDOS = 60

MENSAJE_CODIGO_INVALIDO = "El código no es válido o ya venció. Solicita uno nuevo."


def generar_codigo() -> str:
    """E6: código numérico de 6 dígitos, con generador criptográficamente seguro."""
    return "".join(secrets.choice(string.digits) for _ in range(CODIGO_LONGITUD))


def validar_proposito_codigo(proposito: str) -> None:
    if proposito not in PROPOSITOS_CODIGO:
        raise CodigoVerificacionError(f"El propósito «{proposito}» no es válido.")


def formato_codigo_valido(codigo: str) -> bool:
    return re.fullmatch(rf"\d{{{CODIGO_LONGITUD}}}", codigo or "") is not None


def calcular_vencimiento(ahora: datetime) -> datetime:
    """E6: el código vence a los 10 minutos."""
    return ahora + timedelta(minutes=CODIGO_VIGENCIA_MINUTOS)


def validar_espera_reenvio(fecha_ultimo_codigo: datetime | None, ahora: datetime) -> None:
    """E7: entre un código y el siguiente deben pasar al menos 60 segundos."""
    if fecha_ultimo_codigo is None:
        return
    transcurrido = (ahora - fecha_ultimo_codigo).total_seconds()
    if transcurrido < CODIGO_ESPERA_REENVIO_SEGUNDOS:
        faltan = int(CODIGO_ESPERA_REENVIO_SEGUNDOS - transcurrido) + 1
        raise EsperaReenvioError(f"Espera {faltan} segundos antes de pedir otro código.")


def validar_codigo_utilizable(
    *, usado: bool, intentos: int, vencimiento: datetime, ahora: datetime
) -> None:
    """E8: un código solo sirve si no se usó, no venció y no agotó sus intentos."""
    if usado or intentos >= CODIGO_MAX_INTENTOS or ahora >= vencimiento:
        raise CodigoVerificacionError(MENSAJE_CODIGO_INVALIDO)


def validar_cambio_correo(correo_actual: str, correo_nuevo: str) -> None:
    """El correo nuevo debe ser distinto del actual."""
    if correo_actual.strip().lower() == correo_nuevo.strip().lower():
        raise UsuarioInvalidoError("El nuevo correo debe ser distinto al actual.")


# --- E9: límite de intentos fallidos al cambiar el correo sin sesión ---------
CREDENCIALES_MAX_FALLOS = 5
CREDENCIALES_VENTANA_MINUTOS = 15
