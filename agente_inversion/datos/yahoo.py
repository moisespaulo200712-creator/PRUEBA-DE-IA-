"""Proveedor de datos vía Yahoo Finance (gratis, sin registro).

Emisoras mexicanas usan sufijo .MX, por ejemplo: AMXB.MX, WALMEX.MX.
"""
import pandas as pd

from .base import ProveedorDatos


class ProveedorYahoo(ProveedorDatos):
    nombre = "yahoo"

    def historico(self, emisora: str, dias: int = 180) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "Falta yfinance. Instálalo con: pip install yfinance"
            ) from e

        periodo = f"{max(dias, 30)}d"
        df = yf.download(
            emisora,
            period=periodo,
            interval="1d",
            progress=False,
            auto_adjust=False,
        )
        if df is None or df.empty:
            raise ValueError(
                f"No se obtuvieron datos para '{emisora}'. "
                "¿El ticker es correcto? (ej. AMXB.MX)"
            )

        # yfinance puede devolver columnas multi-nivel; las aplanamos.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.rename(
            columns={
                "Open": "apertura",
                "High": "maximo",
                "Low": "minimo",
                "Close": "cierre",
                "Volume": "volumen",
            }
        )
        df.index.name = "fecha"
        return df[["apertura", "maximo", "minimo", "cierre", "volumen"]].dropna()
