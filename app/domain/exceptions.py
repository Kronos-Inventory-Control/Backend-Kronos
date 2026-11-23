"""
Errores de las reglas de negocio de Kronos.

Son excepciones de Python puro: no dependen de FastAPI ni de la base de datos.
La capa API las traduce a respuestas HTTP (ver `app/main.py`):
    PermisoDenegadoError -> 403
    cualquier otra ReglaDeNegocioError -> 400
"""


class ReglaDeNegocioError(Exception):
    """Se intentó una operación que viola una regla de negocio."""


# --- Inventario y materiales (A) --------------------------------------------
class CantidadInvalidaError(ReglaDeNegocioError):
    """La cantidad debe ser mayor que cero."""


class StockInsuficienteError(ReglaDeNegocioError):
    """La salida supera las existencias disponibles."""


class StockNegativoError(ReglaDeNegocioError):
    """La cantidad disponible de un material no puede ser negativa."""


class MaterialAgotadoError(ReglaDeNegocioError):
    """Un material agotado no puede venderse."""


class MaterialDescontinuadoError(ReglaDeNegocioError):
    """Un material descontinuado no puede ofrecerse para nuevas ventas."""


# --- Ventas (B) -------------------------------------------------------------
class PrecioInvalidoError(ReglaDeNegocioError):
    """El precio de venta debe ser válido y no negativo."""


class VentaInvalidaError(ReglaDeNegocioError):
    """La venta no cumple las condiciones mínimas (detalle, cliente)."""


# --- Órdenes de compra (C) y garantías (D) ----------------------------------
class OrdenCompraInvalidaError(ReglaDeNegocioError):
    """La orden de compra no cumple las condiciones mínimas."""


class OrdenYaRecibidaError(ReglaDeNegocioError):
    """La orden ya fue recibida: no puede recibirse ni generar otra entrada."""


class GarantiaInvalidaError(ReglaDeNegocioError):
    """La garantía no cumple las condiciones mínimas."""


class TransicionInvalidaError(ReglaDeNegocioError):
    """El cambio de estado no respeta el flujo permitido."""


# --- Usuarios y roles (E) ---------------------------------------------------
class UsuarioInvalidoError(ReglaDeNegocioError):
    """Los datos del usuario no cumplen las reglas (rol, perfiles, identificación)."""


class PermisoDenegadoError(ReglaDeNegocioError):
    """El rol del usuario no permite ejecutar la operación."""
