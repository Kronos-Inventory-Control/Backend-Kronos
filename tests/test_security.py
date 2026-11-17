import pytest

from app.core.security import hash_password, verify_password


def test_hash_y_verificacion_de_contrasena():
    hashed = hash_password("MiClaveSegura2026")

    assert hashed != "MiClaveSegura2026"
    assert verify_password("MiClaveSegura2026", hashed) is True
    assert verify_password("OtraClave2026", hashed) is False


def test_contrasena_corta_es_rechazada():
    with pytest.raises(ValueError):
        hash_password("corta")
