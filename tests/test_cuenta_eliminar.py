from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.api.v1 import cuenta
from app.api.v1.cuenta import EliminarCuentaIn, eliminar_mi_cuenta
from app.domain.enums.user_role import UserRole


def _cliente():
    return SimpleNamespace(
        identificacion=12345,
        rol_idRol=int(UserRole.CLIENTE),
        contrasena="hash-de-prueba",
        activo=True,
        nombre="Ana",
        apellidos="Pérez",
        telefono="3000000000",
        correoElectronico="ana@example.com",
        direccion_idDireccion=12,
    )


def test_eliminar_cuenta_inhabilita_anonimiza_y_revoca_sesiones(monkeypatch):
    usuario = _cliente()
    direccion = SimpleNamespace(barrio="Centro", localidad="Usme", direccionCompleta="Calle 1")
    db = Mock()
    db.get.return_value = direccion
    monkeypatch.setattr(cuenta, "verify_password", lambda *_: True)

    respuesta = eliminar_mi_cuenta(EliminarCuentaIn(password="ClaveCorrecta"), db, usuario)

    assert respuesta.status_code == 204
    assert usuario.activo is False
    assert usuario.nombre == "Cuenta"
    assert usuario.apellidos == "eliminada"
    assert usuario.correoElectronico.endswith("@cuenta.invalid")
    assert direccion.direccionCompleta == "Datos eliminados"
    assert db.execute.call_count == 2
    db.commit.assert_called_once()


def test_eliminar_cuenta_rechaza_contrasena_incorrecta(monkeypatch):
    db = Mock()
    monkeypatch.setattr(cuenta, "verify_password", lambda *_: False)

    with pytest.raises(HTTPException) as error:
        eliminar_mi_cuenta(EliminarCuentaIn(password="incorrecta"), db, _cliente())

    assert error.value.status_code == 400
    db.commit.assert_not_called()


def test_eliminar_cuenta_no_permite_borrar_usuarios_internos():
    usuario = _cliente()
    usuario.rol_idRol = int(UserRole.JEFE)
    db = Mock()

    with pytest.raises(HTTPException) as error:
        eliminar_mi_cuenta(EliminarCuentaIn(password="ClaveCorrecta"), db, usuario)

    assert error.value.status_code == 403
    db.commit.assert_not_called()
