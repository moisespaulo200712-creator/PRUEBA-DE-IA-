"""Capa de datos: proveedores de precios intercambiables."""
from .base import ProveedorDatos
from .yahoo import ProveedorYahoo
from .databursatil import ProveedorDataBursatil


def obtener_proveedor(nombre: str) -> ProveedorDatos:
    """Devuelve el proveedor de datos según su nombre."""
    proveedores = {
        "yahoo": ProveedorYahoo,
        "databursatil": ProveedorDataBursatil,
    }
    if nombre not in proveedores:
        raise ValueError(
            f"Fuente '{nombre}' no válida. Opciones: {list(proveedores)}"
        )
    return proveedores[nombre]()
