"""D. Garantías."""

from collections.abc import Sequence
from datetime import datetime

from app.domain.enums.estados import EstadoGarantia
from app.domain.exceptions import GarantiaInvalidaError, TransicionInvalidaError

# D5: enviado -> en revisión -> resuelto. Una garantía resuelta no vuelve a revisión (D4).
TRANSICIONES: dict[EstadoGarantia, frozenset[EstadoGarantia]] = {
    EstadoGarantia.ENVIADO: frozenset({EstadoGarantia.EN_REVISION}),
    EstadoGarantia.EN_REVISION: frozenset({EstadoGarantia.RESUELTO}),
    EstadoGarantia.RESUELTO: frozenset(),
}


def normalizar_estado(valor: str | EstadoGarantia) -> EstadoGarantia:
    try:
        return EstadoGarantia(valor)
    except ValueError:
        permitidos = ", ".join(e.value for e in EstadoGarantia)
        raise TransicionInvalidaError(
            f'Estado de garantía no permitido: "{valor}". Estados válidos: {permitidos}.'
        ) from None


def validar_creacion(referencia_compra: str | int | None, fecha_solicitud: datetime | None) -> None:
    """D1 + D2: ligada a una compra/producto adquirido y con fecha de solicitud."""
    if referencia_compra is None or str(referencia_compra).strip() == "":
        raise GarantiaInvalidaError(
            "Una garantía debe estar relacionada con una compra o producto adquirido."
        )
    if fecha_solicitud is None:
        raise GarantiaInvalidaError("Una garantía debe tener una fecha de solicitud.")


def validar_transicion(actual: str | EstadoGarantia, nuevo: str | EstadoGarantia) -> None:
    """D3 + D4 + D5."""
    actual, nuevo = normalizar_estado(actual), normalizar_estado(nuevo)
    if nuevo not in TRANSICIONES[actual]:
        raise TransicionInvalidaError(
            f"No se puede pasar una garantía de «{actual.value}» a «{nuevo.value}»."
        )


def validar_observaciones_conservadas(previas: Sequence, nuevas: Sequence | None) -> None:
    """D6: una actualización puede agregar observaciones, nunca borrar las anteriores."""
    if nuevas is None:
        return
    if list(nuevas[: len(previas)]) != list(previas):
        raise GarantiaInvalidaError(
            "No se pueden eliminar ni modificar las observaciones ya registradas."
        )
