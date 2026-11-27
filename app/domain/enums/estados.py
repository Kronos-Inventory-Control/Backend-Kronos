"""Estados permitidos por las reglas de negocio de Kronos."""

import enum


class TipoMovimiento(enum.Enum):
    ENTRADA = "entrada"
    SALIDA = "salida"


class EstadoStock(str, enum.Enum):
    """Estado del inventario; se deduce SIEMPRE de la cantidad disponible (regla A8)."""

    DISPONIBLE = "disponible"
    BAJO = "bajo"  # en o por debajo del umbral mínimo
    AGOTADO = "agotado"  # stock = 0
    DESCONTINUADO = "descontinuado"


class EstadoOrdenCompra(str, enum.Enum):
    """Regla C5: pendiente, enviada y recibida."""

    PENDIENTE = "pendiente"
    ENVIADA = "enviada"
    RECIBIDA = "recibida"


class EstadoGarantia(str, enum.Enum):
    """Regla D3: enviado, en revisión y resuelto."""

    ENVIADO = "enviado"
    EN_REVISION = "en_revision"
    RESUELTO = "resuelto"
