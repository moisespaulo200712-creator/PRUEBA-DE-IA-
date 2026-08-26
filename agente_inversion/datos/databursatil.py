"""Proveedor de datos vía DataBursatil (BMV/BIVA, datos oficiales México).

Gratis con registro: https://databursatil.com/  (créditos mensuales renovables).
Documentación: https://www.databursatil.com/docs.html

Endpoint usado (API v2, confirmado contra la doc oficial):

    GET https://api.databursatil.com/v2/historicos
        token          -> tu token (desde .env)
        emisora_serie  -> UNA emisora CON serie. Ej: "ALSEA*", "GFNORTEO", "WALMEX*"
        inicio         -> fecha inicial AAAA-MM-DD
        final          -> fecha final   AAAA-MM-DD

    Respuesta: por cada día devuelve `precio` (cierre) e `importe` (monto
    operado en pesos). OJO: este endpoint NO trae apertura/máximo/mínimo ni
    volumen en acciones. Por eso:
        - precio  -> cierre
        - importe -> volumen  (se usa como PROXY de actividad para vol_rel)
        - apertura/maximo/minimo se rellenan con el cierre para que los
          indicadores basados en cierre (RSI, MACD, medias, Bollinger) sigan
          funcionando sin cambios en el resto del agente.

⚠️ Con esta fuente no hay velas OHLC reales; las señales de "movimiento fuerte"
   se calculan sobre el cierre día a día, no sobre el rango intradía.
"""
import pandas as pd
import requests

import config
from .base import ProveedorDatos

_URL_BASE = "https://api.databursatil.com/v2"


def _a_emisora_serie(emisora: str) -> str:
    """Normaliza el ticker recibido al formato que espera DataBursatil.

    - Quita el sufijo ".MX" de Yahoo si viene (WALMEX.MX -> WALMEX).
    - Respeta la serie si ya viene (GFNORTEO, ALSEA*, AMXB, etc.).

    No inventamos la serie: DataBursatil requiere emisora CON serie, así que si
    solo pasas "WALMEX" puede que necesites "WALMEX*". Pasa el ticker completo.
    """
    e = emisora.strip().upper()
    if e.endswith(".MX"):
        e = e[:-3]
    return e


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
            "emisora_serie": _a_emisora_serie(emisora),
            "inicio": inicio.strftime("%Y-%m-%d"),
            "final": fin.strftime("%Y-%m-%d"),
        }
        try:
            resp = requests.get(
                f"{_URL_BASE}/historicos", params=params, timeout=30
            )
            resp.raise_for_status()
        except requests.HTTPError as e:
            raise ValueError(self._mensaje_http(e)) from e
        except requests.RequestException as e:
            raise ValueError(f"Error de conexión con DataBursatil: {e}") from e

        datos = resp.json()
        df = self._normalizar(datos)
        if df.empty:
            raise ValueError(
                f"DataBursatil no devolvió datos para '{emisora}'. "
                "Verifica la emisora CON serie (ej. WALMEX*) y tu token."
            )
        return df

    @staticmethod
    def _mensaje_http(e: requests.HTTPError) -> str:
        """Traduce los códigos de error de DataBursatil a algo legible."""
        cod = e.response.status_code if e.response is not None else "?"
        mensajes = {
            400: "Parámetros inválidos. Revisa emisora_serie y las fechas.",
            401: "Token inválido o expirado. Revisa tu DATABURSATIL_TOKEN.",
            403: "Acceso denegado (la API solo acepta GET).",
            429: "Créditos agotados. Se renuevan el día 1 de cada mes.",
        }
        return f"DataBursatil HTTP {cod}: {mensajes.get(cod, 'error de la API')}"

    @staticmethod
    def _normalizar(datos) -> pd.DataFrame:
        """Convierte la respuesta JSON de /v2/historicos al formato estándar.

        La API puede devolver la serie de dos formas; soportamos ambas:
          A) dict indexado por fecha:
               {"2025-06-02": {"precio": 12.3, "importe": 456}, ...}
               {"2025-06-02": [12.3, 456], ...}
               {"2025-06-02": 12.3, ...}           (solo cierre)
          B) lista de registros:
               [{"fecha": "2025-06-02", "precio": 12.3, "importe": 456}, ...]
        """
        if isinstance(datos, dict) and "error" in datos:
            raise ValueError(f"DataBursatil: {datos['error']}")

        registros = _registros_desde(datos)
        if not registros:
            return pd.DataFrame()

        df = pd.DataFrame(registros)
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df = df.dropna(subset=["fecha"]).set_index("fecha").sort_index()

        df["cierre"] = pd.to_numeric(df.get("precio"), errors="coerce")
        # Sin OHLC real: rellenamos con el cierre para no romper indicadores.
        for col in ("apertura", "maximo", "minimo"):
            df[col] = df["cierre"]
        # Importe operado (pesos) como proxy de "volumen"/actividad.
        df["volumen"] = pd.to_numeric(df.get("importe", 0), errors="coerce").fillna(0)

        cols = ["apertura", "maximo", "minimo", "cierre", "volumen"]
        return df[cols].dropna(subset=["cierre"])


def _registros_desde(datos) -> list[dict]:
    """Aplana cualquiera de las formas de respuesta a [{fecha, precio, importe}]."""
    # Desenvuelve un posible wrapper {"data": ...}
    if isinstance(datos, dict) and "data" in datos and len(datos) == 1:
        datos = datos["data"]

    registros: list[dict] = []

    if isinstance(datos, dict):
        for fecha, valor in datos.items():
            reg = {"fecha": fecha}
            if isinstance(valor, dict):
                v = {k.lower(): x for k, x in valor.items()}
                reg["precio"] = v.get("precio", v.get("cierre", v.get("close")))
                reg["importe"] = v.get("importe", v.get("volumen", 0))
            elif isinstance(valor, (list, tuple)):
                reg["precio"] = valor[0] if len(valor) > 0 else None
                reg["importe"] = valor[1] if len(valor) > 1 else 0
            else:  # escalar => solo cierre
                reg["precio"] = valor
                reg["importe"] = 0
            registros.append(reg)

    elif isinstance(datos, list):
        for item in datos:
            if not isinstance(item, dict):
                continue
            v = {k.lower(): x for k, x in item.items()}
            registros.append({
                "fecha": v.get("fecha", v.get("date")),
                "precio": v.get("precio", v.get("cierre", v.get("close"))),
                "importe": v.get("importe", v.get("volumen", 0)),
            })

    return registros
