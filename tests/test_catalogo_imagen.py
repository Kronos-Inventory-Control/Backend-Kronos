import base64

import pytest
from fastapi import HTTPException

from app.api.v1.catalogo import _imagen_desde_base64, _tipo_imagen


# PNG transparente de 1×1 píxel; basta para verificar la validación sin I/O.
PNG_1X1 = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/"
    "a0K3mQAAAABJRU5ErkJggg=="
)


def test_imagen_base64_acepta_png_y_detecta_su_tipo():
    imagen = _imagen_desde_base64(PNG_1X1)

    assert imagen is not None
    assert _tipo_imagen(imagen) == "image/png"


def test_imagen_base64_rechaza_contenido_que_no_es_imagen():
    texto = base64.b64encode(b"esto no es una imagen").decode()

    with pytest.raises(HTTPException) as error:
        _imagen_desde_base64(texto)

    assert error.value.status_code == 422
