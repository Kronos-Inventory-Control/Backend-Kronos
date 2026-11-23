import pytest
from pydantic import ValidationError

from app.domain.enums.user_role import UserRole
from app.schemas.user import UserCreate, UserStatusUpdate, UserUpdate

BASE = {
    "nombre": "Laura",
    "apellidos": "Gómez",
    "email": "laura@kronos.com",
    "password": "ClaveMuySegura2026",
}


def test_crea_empleado_sin_perfiles_y_acepta_rol_por_nombre():
    u = UserCreate(**BASE, rol="EMPLEADO")
    assert u.rol == UserRole.EMPLEADO


def test_acepta_rol_por_numero():
    assert UserCreate(**BASE, rol=3).rol == UserRole.JEFE


def test_no_se_puede_crear_super_admin():
    with pytest.raises(ValidationError):
        UserCreate(**BASE, rol="SUPER_ADMIN")


def test_proveedor_exige_su_perfil():
    with pytest.raises(ValidationError):
        UserCreate(**BASE, rol="PROVEEDOR")
    u = UserCreate(**BASE, rol="PROVEEDOR", perfil_proveedor={"tipoProducto": "Herramientas"})
    assert u.perfil_proveedor.tipoProducto == "Herramientas"


def test_perfiles_incompatibles_con_el_rol_se_rechazan():
    with pytest.raises(ValidationError):
        UserCreate(**BASE, rol="CLIENTE", perfil_proveedor={"tipoProducto": "X1"})
    with pytest.raises(ValidationError):
        UserCreate(**BASE, rol="JEFE", perfil_cliente={})


def test_contrasena_minimo_12_caracteres():
    with pytest.raises(ValidationError):
        UserCreate(**{**BASE, "password": "corta123"}, rol="CLIENTE")


def test_update_no_permite_cambiar_el_rol():
    with pytest.raises(ValidationError):
        UserUpdate(rol=3)
    assert UserUpdate(telefono="3001234567").model_dump(exclude_unset=True) == {
        "telefono": "3001234567"
    }


def test_cambio_de_estado():
    assert UserStatusUpdate(activo=False).activo is False
