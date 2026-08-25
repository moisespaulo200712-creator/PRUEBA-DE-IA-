"""Indicadores técnicos, calculados con puro pandas (sin dependencias pesadas)."""
import pandas as pd


def sma(serie: pd.Series, ventana: int) -> pd.Series:
    """Media móvil simple."""
    return serie.rolling(window=ventana).mean()


def ema(serie: pd.Series, ventana: int) -> pd.Series:
    """Media móvil exponencial."""
    return serie.ewm(span=ventana, adjust=False).mean()


def rsi(serie: pd.Series, ventana: int = 14) -> pd.Series:
    """Índice de Fuerza Relativa (RSI). Valores de 0 a 100."""
    delta = serie.diff()
    ganancia = delta.clip(lower=0).rolling(window=ventana).mean()
    perdida = (-delta.clip(upper=0)).rolling(window=ventana).mean()
    rs = ganancia / perdida.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))


def macd(serie: pd.Series, rapida: int = 12, lenta: int = 26, senal: int = 9):
    """MACD. Devuelve (linea_macd, linea_senal, histograma)."""
    macd_linea = ema(serie, rapida) - ema(serie, lenta)
    macd_senal = ema(macd_linea, senal)
    return macd_linea, macd_senal, macd_linea - macd_senal


def bollinger(serie: pd.Series, ventana: int = 20, desv: float = 2.0):
    """Bandas de Bollinger. Devuelve (banda_media, superior, inferior)."""
    media = sma(serie, ventana)
    sd = serie.rolling(window=ventana).std()
    return media, media + desv * sd, media - desv * sd


def volumen_relativo(volumen: pd.Series, ventana: int = 20) -> pd.Series:
    """Volumen del día respecto al promedio (1.0 = normal, 2.0 = el doble)."""
    promedio = volumen.rolling(window=ventana).mean()
    return volumen / promedio.replace(0, 1e-9)


def calcular_todos(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega todas las columnas de indicadores al DataFrame de precios."""
    df = df.copy()
    cierre = df["cierre"]
    df["sma20"] = sma(cierre, 20)
    df["sma50"] = sma(cierre, 50)
    df["ema12"] = ema(cierre, 12)
    df["rsi"] = rsi(cierre)
    df["macd"], df["macd_senal"], df["macd_hist"] = macd(cierre)
    df["bb_media"], df["bb_sup"], df["bb_inf"] = bollinger(cierre)
    df["vol_rel"] = volumen_relativo(df["volumen"])
    df["cambio_pct"] = cierre.pct_change() * 100
    return df
