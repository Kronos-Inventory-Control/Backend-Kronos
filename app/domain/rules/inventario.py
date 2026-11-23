"""A. Inventario y materiales."""

from app.domain.enums.estados import EstadoStock
from app.domain.exceptions import (
    CantidadInvalidaError,
    MaterialAgotadoError,
    MaterialDescontinuadoError,
    StockInsuficienteError,
    StockNegativoError,
)


def validar_cantidad_positiva(cantidad: int, etiqueta: str = "La cantidad") -> None:
    """A5 / B2 / C3: las cantidades deben ser mayores que cero."""
    if cantidad <= 0:
        raise CantidadInvalidaError(f"{etiqueta} debe ser mayor que cero.")


def validar_stock_no_negativo(stock: int) -> None:
    """A1: la cantidad disponible nunca puede ser negativa."""
    if stock < 0:
        raise StockNegativoError("La cantidad disponible no puede ser negativa.")


def validar_salida(stock: int, cantidad: int, nombre: str = "el material") -> None:
    """A2 / B1: no se puede sacar más de lo que hay."""
    validar_cantidad_positiva(cantidad)
    if cantidad > stock:
        raise StockInsuficienteError(
            f'Stock insuficiente de "{nombre}": solo hay {stock} disponible(s).'
        )


def aplicar_entrada(stock: int, cantidad: int) -> int:
    """A3: las entradas aumentan las existencias. Devuelve el nuevo stock."""
    validar_cantidad_positiva(cantidad)
    return stock + cantidad


def aplicar_salida(stock: int, cantidad: int, nombre: str = "el material") -> int:
    """A4: las salidas disminuyen las existencias. Devuelve el nuevo stock."""
    validar_salida(stock, cantidad, nombre)
    nuevo = stock - cantidad
    validar_stock_no_negativo(nuevo)
    return nuevo


def validar_material_vendible(
    stock: int, cantidad: int, nombre: str = "el material", descontinuado: bool = False
) -> None:
    """A6 / A7 / B1: un material agotado o descontinuado no se vende."""
    if descontinuado:
        raise MaterialDescontinuadoError(
            f'"{nombre}" está descontinuado y no puede ofrecerse para nuevas ventas.'
        )
    if stock <= 0:
        raise MaterialAgotadoError(f'"{nombre}" está agotado y no puede venderse.')
    validar_salida(stock, cantidad, nombre)


def calcular_estado_stock(
    stock: int, umbral_minimo: int, descontinuado: bool = False
) -> EstadoStock:
    """A8: el estado del inventario corresponde a la cantidad disponible."""
    validar_stock_no_negativo(stock)
    if descontinuado:
        return EstadoStock.DESCONTINUADO
    if stock == 0:
        return EstadoStock.AGOTADO
    if stock <= umbral_minimo:
        return EstadoStock.BAJO
    return EstadoStock.DISPONIBLE


def requiere_alerta(stock: int, umbral_minimo: int) -> bool:
    """A9: se alerta cuando las existencias alcanzan (o bajan de) el mínimo."""
    return stock <= umbral_minimo
