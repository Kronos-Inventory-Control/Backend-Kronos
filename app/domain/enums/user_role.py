import enum


class UserRole(enum.IntEnum):
    CLIENTE = 1
    PROVEEDOR = 2
    JEFE = 3
    EMPLEADO = 4
    SUPER_ADMIN = 5