from datetime import datetime, timedelta

import pytest

from app.domain.exceptions import (
    CodigoVerificacionError,
    EsperaReenvioError,
    UsuarioInvalidoError,
)
from app.domain.rules.usuarios import (
    CODIGO_LONGITUD,
    CODIGO_MAX_INTENTOS,
    calcular_vencimiento,
    formato_codigo_valido,
    generar_codigo,
    validar_cambio_correo,
    validar_codigo_utilizable,
    validar_espera_reenvio,
    validar_proposito_codigo,
)

AHORA = datetime(2026, 11, 24, 12, 0, 0)


def test_codigo_generado_tiene_6_digitos():
    for _ in range(50):
        codigo = generar_codigo()
        assert len(codigo) == CODIGO_LONGITUD and formato_codigo_valido(codigo)


@pytest.mark.parametrize("valor", ["", "12345", "1234567", "12a456", "12 456", None])
def test_formato_invalido(valor):
    assert not formato_codigo_valido(valor)


def test_vigencia_de_10_minutos():
    assert calcular_vencimiento(AHORA) == AHORA + timedelta(minutes=10)


def test_codigo_vencido_usado_o_sin_intentos_se_rechaza():
    venc = calcular_vencimiento(AHORA)
    validar_codigo_utilizable(usado=False, intentos=0, vencimiento=venc, ahora=AHORA)
    with pytest.raises(CodigoVerificacionError):
        validar_codigo_utilizable(usado=False, intentos=0, vencimiento=venc, ahora=venc)
    with pytest.raises(CodigoVerificacionError):
        validar_codigo_utilizable(usado=True, intentos=0, vencimiento=venc, ahora=AHORA)
    with pytest.raises(CodigoVerificacionError):
        validar_codigo_utilizable(
            usado=False, intentos=CODIGO_MAX_INTENTOS, vencimiento=venc, ahora=AHORA
        )


def test_espera_de_reenvio_de_60_segundos():
    validar_espera_reenvio(None, AHORA)
    validar_espera_reenvio(AHORA - timedelta(seconds=61), AHORA)
    with pytest.raises(EsperaReenvioError):
        validar_espera_reenvio(AHORA - timedelta(seconds=10), AHORA)


def test_proposito_desconocido_se_rechaza():
    validar_proposito_codigo("CAMBIAR_CORREO")
    with pytest.raises(CodigoVerificacionError):
        validar_proposito_codigo("OTRO")


def test_correo_nuevo_debe_ser_distinto():
    validar_cambio_correo("a@kronos.com", "b@kronos.com")
    with pytest.raises(UsuarioInvalidoError):
        validar_cambio_correo("A@kronos.com", "a@KRONOS.com")


def test_limitador_bloquea_tras_5_fallos_y_se_limpia():
    from app.services.limitador import LimitadorIntentos

    lim = LimitadorIntentos(maximo=5, ventana_segundos=900)
    for _ in range(4):
        lim.registrar_fallo("id:1", "ip:x")
    assert not lim.bloqueado("id:1", "ip:x")
    lim.registrar_fallo("id:1", "ip:x")
    assert lim.bloqueado("id:1")
    assert lim.bloqueado("id:2", "ip:x")  # basta con que una clave esté bloqueada
    assert not lim.bloqueado("id:2")
    lim.limpiar("id:1", "ip:x")
    assert not lim.bloqueado("id:1", "ip:x")


def test_limitador_olvida_fallos_fuera_de_la_ventana():
    from app.services.limitador import LimitadorIntentos

    lim = LimitadorIntentos(maximo=2, ventana_segundos=0)
    lim.registrar_fallo("a")
    lim.registrar_fallo("a")
    assert not lim.bloqueado("a")
