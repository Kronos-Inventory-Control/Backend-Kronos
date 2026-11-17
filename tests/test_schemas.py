from datetime import datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.domain.enums.user_role import UserRole
from app.schemas import LoginRequest, TokenResponse, UserResponse


def test_login_request_valida_correo():
    assert LoginRequest(email="a@b.com", password="x").email == "a@b.com"
    with pytest.raises(ValidationError):
        LoginRequest(email="no-es-correo", password="x")


def test_token_response_por_defecto_es_bearer():
    assert TokenResponse(access_token="t", expires_in=7200).token_type == "bearer"


def test_user_response_no_expone_contrasena():
    usuario = SimpleNamespace(
        identificacion=1,
        nombre="Ana",
        apellidos="Pérez",
        correoElectronico="ana@kronos.com",
        telefono="3000000000",
        rol_idRol=5,
        activo=True,
        fechaCreacion=datetime(2026, 1, 1),
        fechaActualizacion=datetime(2026, 1, 1),
        contrasena="hash-secreto",
    )

    data = UserResponse.model_validate(usuario).model_dump()

    assert data["rol"] == UserRole.SUPER_ADMIN
    assert "contrasena" not in data
