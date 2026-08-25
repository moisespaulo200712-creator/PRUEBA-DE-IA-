"""Interfaz común para cualquier proveedor de datos de mercado.

Si mañana quieres agregar otra fuente (BIVA directo, otro broker, etc.),
solo crea una clase que herede de ProveedorDatos e implementa `historico`.
Así el resto del agente no cambia.
"""
from abc import ABC, abstractmethod
import pandas as pd


class ProveedorDatos(ABC):
    """Contrato que todo proveedor de datos debe cumplir."""

    nombre: str = "base"

    @abstractmethod
    def historico(self, emisora: str, dias: int = 180) -> pd.DataFrame:
        """Devuelve el histórico de precios de una emisora.

        El DataFrame resultante DEBE tener estas columnas (en minúsculas):
            fecha (índice), apertura, maximo, minimo, cierre, volumen

        Args:
            emisora: clave/ticker de la emisora.
            dias: cuántos días hacia atrás traer.
        """
        raise NotImplementedError
