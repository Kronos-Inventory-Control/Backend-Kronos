import enum


class UserRole(enum.IntEnum):
    """Ids de la tabla `roles` (se usan en la autenticación)."""

    CLIENTE = 1
    PROVEEDOR = 2
    JEFE = 3
    EMPLEADO = 4
    SUPER_ADMIN = 5  # único; se crea solo con scripts/create_super_admin.py
