"""
Límite de intentos fallidos de cédula/contraseña (cambio de correo sin sesión).

Está en memoria: sirve con un solo proceso de uvicorn. Si algún día se corre
con varios workers, hay que moverlo a una tabla o a Redis.
"""

import time
from threading import Lock

from app.domain.rules.usuarios import CREDENCIALES_MAX_FALLOS, CREDENCIALES_VENTANA_MINUTOS


class LimitadorIntentos:
    def __init__(self, maximo: int = CREDENCIALES_MAX_FALLOS,
                 ventana_segundos: int = CREDENCIALES_VENTANA_MINUTOS * 60):
        self.maximo = maximo
        self.ventana = ventana_segundos
        self._fallos: dict[str, list[float]] = {}
        self._lock = Lock()

    def _vigentes(self, clave: str, ahora: float) -> list[float]:
        vigentes = [t for t in self._fallos.get(clave, []) if ahora - t < self.ventana]
        if vigentes:
            self._fallos[clave] = vigentes
        else:
            self._fallos.pop(clave, None)
        return vigentes

    def bloqueado(self, *claves: str) -> bool:
        ahora = time.monotonic()
        with self._lock:
            return any(len(self._vigentes(c, ahora)) >= self.maximo for c in claves)

    def registrar_fallo(self, *claves: str) -> None:
        ahora = time.monotonic()
        with self._lock:
            for c in claves:
                self._vigentes(c, ahora)
                self._fallos.setdefault(c, []).append(ahora)

    def limpiar(self, *claves: str) -> None:
        with self._lock:
            for c in claves:
                self._fallos.pop(c, None)
