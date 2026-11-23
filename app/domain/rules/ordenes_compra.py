"""C. Órdenes de compra."""

from collections.abc import Sequence

from app.domain.enums.estados import EstadoOrdenCompra
from app.domain.exceptions import (
    OrdenCompraInvalidaError,
    OrdenYaRecibidaError,
    TransicionInvalidaError,
)
from app.domain.rules.inventario import validar_cantidad_positiva

# C5: flujo permitido (solo hacia adelante).
TRANSICIONES: dict[EstadoOrdenCompra, frozenset[EstadoOrdenCompra]] = {
    EstadoOrdenCompra.PENDIENTE: frozenset({EstadoOrdenCompra.ENVIADA}),
    EstadoOrdenCompra.ENVIADA: frozenset({EstadoOrdenCompra.RECIBIDA}),
    EstadoOrdenCompra.RECIBIDA: frozenset(),
}


def normalizar_estado(valor: str | EstadoOrdenCompra) -> EstadoOrdenCompra:
    try:
        return EstadoOrdenCompra(valor)
    except ValueError:
        permitidos = ", ".join(e.value for e in EstadoOrdenCompra)
        raise TransicionInvalidaError(
            f'Estado de orden no permitido: "{valor}". Estados válidos: {permitidos}.'
        ) from None


def validar_orden(proveedor_id: int | None, cantidades: Sequence[int]) -> None:
    """C1 + C2 + C3: proveedor, al menos un material y cantidades > 0."""
    if proveedor_id is None:
        raise OrdenCompraInvalidaError("Una orden de compra debe estar asociada a un proveedor.")
    if len(cantidades) < 1:
        raise OrdenCompraInvalidaError("Una orden de compra debe contener al menos un material.")
    for cantidad in cantidades:
        validar_cantidad_positiva(cantidad, "La cantidad solicitada")


def validar_transicion(actual: str | EstadoOrdenCompra, nuevo: str | EstadoOrdenCompra) -> None:
    """C5 + C6: respeta el flujo y no se recibe una orden ya recibida."""
    actual, nuevo = normalizar_estado(actual), normalizar_estado(nuevo)
    if actual == EstadoOrdenCompra.RECIBIDA and nuevo == EstadoOrdenCompra.RECIBIDA:
        raise OrdenYaRecibidaError("La orden ya fue recibida; no se puede recibir de nuevo.")
    if nuevo not in TRANSICIONES[actual]:
        raise TransicionInvalidaError(
            f"No se puede pasar una orden de «{actual.value}» a «{nuevo.value}»."
        )


def genera_entrada(actual: str | EstadoOrdenCompra, nuevo: str | EstadoOrdenCompra) -> bool:
    """C4: la entrada de materiales se genera UNA sola vez, al pasar a «recibida»."""
    actual, nuevo = normalizar_estado(actual), normalizar_estado(nuevo)
    return nuevo == EstadoOrdenCompra.RECIBIDA and actual != EstadoOrdenCompra.RECIBIDA
