from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)

RUTA = "/api/v1/auth/login"


def _preflight(origin: str):
    return client.options(
        RUTA,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )


def test_origen_permitido_recibe_cabeceras_cors():
    origin = settings.cors_origins_list[0]

    response = _preflight(origin)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_origen_no_permitido_es_rechazado():
    response = _preflight("http://sitio-no-autorizado.com")

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
