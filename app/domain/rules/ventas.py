"""B. Ventas."""

from decimal import Decimal

from app.domain.exceptions import PrecioInvalidoError, VentaInvalidaError
from app.domain.rules.inventario import validar_cantidad_positiva, validar_material_vendible


def validar_precio_venta(precio: Decimal | int | float | None) -> None:
    """B4: el precio de venta debe ser válido y no negativo."""
    if precio is None or precio < 0:
        raise PrecioInvalidoError("El precio de venta debe ser un valor válido y no negativo.")


def validar_linea_venta(
    cantidad: int,
    precio: Decimal | int | float | None,
    stock: int,
    nombre: str = "el material",
    descontinuado: bool = False,
) -> None:
    """B1 + B2 + B4 (y A6/A7) para un renglón de la venta."""
    validar_cantidad_positiva(cantidad, "La cantidad vendida")
    validar_precio_venta(precio)
    validar_material_vendible(stock, cantidad, nombre, descontinuado)


def validar_venta(cantidad_detalles: int, cliente_id: int | None) -> None:
    """B3 + B6: al menos un detalle y un cliente asociado."""
    if cantidad_detalles < 1:
        raise VentaInvalidaError("Una venta debe contener al menos un producto.")
    if cliente_id is None:
        raise VentaInvalidaError("Una venta debe estar asociada a un cliente.")
