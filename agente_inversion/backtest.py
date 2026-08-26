"""Backtesting: mide qué tan seguido acertaron las señales técnicas en el pasado.

La idea es honesta y simple: recorremos TODO el histórico y, en cada día,
calculamos el mismo puntaje técnico que usa el agente. Luego miramos qué pasó
con el precio en los siguientes N días (el "horizonte"). Así respondemos:

    "Cuando el agente dio 🟢, ¿cuántas veces subió el precio después,
     y cuánto en promedio?"

Comparamos cada tipo de señal contra un BASELINE (comprar cualquier día al
azar). Si la señal no le gana al baseline, entonces no aporta nada: es humo.

⚠️ Esto mide el pasado. El pasado NO garantiza el futuro. Es una herramienta
   para decidir con base, no una promesa de ganancias.
"""
import pandas as pd

import config
from agente_inversion import indicadores

# Columnas de indicadores que deben existir antes de evaluar una fila.
_REQUERIDAS = ["rsi", "sma20", "sma50", "macd", "macd_senal", "bb_inf", "bb_sup"]


def _puntaje_fila(fila) -> int:
    """Mismo puntaje técnico que agentes/tecnico.py, pero para UNA fila.

    Se mantiene en sincronía con la lógica de `tecnico.analizar`.
    """
    p = 0
    rsi = fila["rsi"]
    if rsi <= config.RSI_SOBREVENTA:
        p += 1
    elif rsi >= config.RSI_SOBRECOMPRA:
        p -= 1

    p += 1 if fila["sma20"] > fila["sma50"] else -1
    p += 1 if fila["macd"] > fila["macd_senal"] else -1

    if fila["cierre"] <= fila["bb_inf"]:
        p += 1
    elif fila["cierre"] >= fila["bb_sup"]:
        p -= 1
    return p


def _bucket(puntaje: int) -> str:
    """Agrupa el puntaje en las mismas etiquetas que ve el usuario."""
    if puntaje >= 3:
        return "🟢🟢 Alcista fuerte (+3 o más)"
    if puntaje >= 1:
        return "🟢 Alcista moderado (+1 a +2)"
    if puntaje <= -3:
        return "🔴🔴 Bajista fuerte (-3 o menos)"
    if puntaje <= -1:
        return "🔴 Bajista moderado (-1 a -2)"
    return "⚪ Neutral (0)"


# Orden en que queremos mostrar los buckets.
_ORDEN = [
    "🟢🟢 Alcista fuerte (+3 o más)",
    "🟢 Alcista moderado (+1 a +2)",
    "⚪ Neutral (0)",
    "🔴 Bajista moderado (-1 a -2)",
    "🔴🔴 Bajista fuerte (-3 o menos)",
]


def correr(emisora: str, df: pd.DataFrame, horizonte: int = 10) -> dict:
    """Ejecuta el backtest de una emisora.

    Args:
        emisora: nombre/clave (solo para el reporte).
        df: histórico con columnas estándar (cierre, etc.).
        horizonte: cuántos días hacia adelante medir el rendimiento.

    Returns:
        dict con el resumen por tipo de señal + el baseline.
    """
    ind = indicadores.calcular_todos(df).dropna(subset=_REQUERIDAS).copy()
    if len(ind) <= horizonte + 1:
        raise ValueError(
            f"{emisora}: histórico insuficiente para backtest "
            f"(se necesitan más de {horizonte + 1} días con indicadores)."
        )

    # Rendimiento futuro: precio dentro de N días vs precio de hoy.
    ind["ret_fwd"] = ind["cierre"].shift(-horizonte) / ind["cierre"] - 1.0
    ind = ind.dropna(subset=["ret_fwd"])  # últimos N días no tienen futuro aún

    ind["puntaje"] = ind.apply(_puntaje_fila, axis=1)
    ind["bucket"] = ind["puntaje"].apply(_bucket)

    baseline = _stats(ind["ret_fwd"])

    por_senal = {}
    for nombre in _ORDEN:
        sub = ind.loc[ind["bucket"] == nombre, "ret_fwd"]
        if len(sub) > 0:
            por_senal[nombre] = _stats(sub)

    return {
        "emisora": emisora,
        "horizonte": horizonte,
        "n_dias": len(ind),
        "desde": ind.index.min().strftime("%Y-%m-%d"),
        "hasta": ind.index.max().strftime("%Y-%m-%d"),
        "baseline": baseline,
        "por_senal": por_senal,
    }


def _stats(serie: pd.Series) -> dict:
    """Estadísticas de una serie de rendimientos futuros."""
    return {
        "n": int(len(serie)),
        "aciertos_pct": round(float((serie > 0).mean() * 100), 1),
        "ret_prom_pct": round(float(serie.mean() * 100), 2),
        "ret_mediana_pct": round(float(serie.median() * 100), 2),
        "mejor_pct": round(float(serie.max() * 100), 2),
        "peor_pct": round(float(serie.min() * 100), 2),
    }


def formatear(resultado: dict) -> str:
    """Convierte el resultado del backtest en un reporte legible."""
    r = resultado
    b = r["baseline"]
    lineas = [
        f"📈 BACKTEST: {r['emisora']}",
        f"   Periodo: {r['desde']} → {r['hasta']}  ({r['n_dias']} días analizados)",
        f"   Horizonte: rendimiento a {r['horizonte']} días después de cada señal",
        "",
        f"   📊 BASELINE (comprar cualquier día al azar):",
        f"      Acierto: {b['aciertos_pct']}%  |  Rend. promedio: {b['ret_prom_pct']:+.2f}%",
        "",
        "   POR TIPO DE SEÑAL:",
    ]
    for nombre in _ORDEN:
        s = r["por_senal"].get(nombre)
        if not s:
            continue
        # Comparación contra baseline para saber si la señal aporta.
        delta = s["ret_prom_pct"] - b["ret_prom_pct"]
        marca = "✅ mejor que azar" if delta > 0 else "❌ peor que azar"
        lineas.append(
            f"   {nombre}"
        )
        lineas.append(
            f"      veces: {s['n']:>4}  |  acierto: {s['aciertos_pct']:>5}%  |  "
            f"rend. prom: {s['ret_prom_pct']:+.2f}%  ({marca})"
        )
    lineas.append("")
    lineas.append(
        "   ⚠️ Mide el PASADO. No garantiza el futuro. No es asesoría financiera."
    )
    return "\n".join(lineas)
