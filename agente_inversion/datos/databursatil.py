"""Proveedor de datos vía DataBursatil (BMV/BIVA, datos oficiales México).

Gratis con registro: https://databursatil.com/ (200,000 créditos/mes).
Documentación: https://www.databursatil.com/docs.html

NOTA: Los endpoints y parámetros exactos pueden cambiar; revisa la doc oficial
y ajusta `_URL_BASE` / los nombres de parámetros si es necesario. Este archivo
deja la integración lista y el token se lee desde .env.
"""
import pandas as pd
import requests

import config
from .base import ProveedorDatos

_URL_BASE = "https://api.databursatil.com/v1"


class ProveedorDataBursatil(ProveedorDatos):
    nombre = "databursatil"

    def __init__(self, token: str | None = None):
        self.token = token or config.DATABURSATIL_TOKEN
        if not self.token:
            raise ValueError(
                "Falta DATABURSATIL_TOKEN. Regístrate gratis en "
                "https://databursatil.com/ y ponlo en tu archivo .env"
            )

    def historico(self, emisora: str, dias: int = 180) -> pd.DataFrame:
        fin = pd.Timestamp.today().normalize()
        inicio = fin - pd.Timedelta(days=dias)

        params = {
            "token": self.token,
            "emisora": emisora,
            "bmv": "SI",          # incluir BMV
            "inicio": inicio.strftime("%Y-%m-%d"),
            "final": fin.strftime("%Y-%m-%d"),
        }
        resp = requests.get(f"{_URL_BASE}/precios_historicos", params=params, timeout=30)
        resp.raise_for_status()
        datos = resp.json()

        df = self._normalizar(datos)
        if df.empty:
            raise ValueError(
                f"DataBursatil no devolvió datos para '{emisora}'. "
                "Verifica la clave de la emisora y tu token."
            )
        return df

    @staticmethod
    def _normalizar(datos) -> pd.DataFrame:
        """Convierte la respuesta JSON al formato estándar del agente.

        Se implementa de forma defensiva porque el esquema exacto de la
        respuesta debe confirmarse contra la documentación vigente.
        """
        registros = datos.get("data", datos) if isinstance(datos, dict) else datos
        df = pd.DataFrame(registros)
        if df.empty:
            return df

        # Mapea nombres comunes -> estándar. Ajusta según la doc real.
        mapa = {
            "fecha": "fecha", "date": "fecha",
            "apertura": "apertura", "open": "apertura",
            "maximo": "maximo", "max": "maximo", "high": "maximo",
            "minimo": "minimo", "min": "minimo", "low": "minimo",
            "cierre": "cierre", "ultimo": "cierre", "close": "cierre",
            "volumen": "volumen", "volume": "volumen",
        }
        df = df.rename(columns={c: mapa.get(c.lower(), c) for c in df.columns})
        df["fecha"] = pd.to_datetime(df["fecha"])
        df = df.set_index("fecha").sort_index()

        cols = ["apertura", "maximo", "minimo", "cierre", "volumen"]
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df[[c for c in cols if c in df.columns]].dropna()
