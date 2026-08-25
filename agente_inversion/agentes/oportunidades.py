"""Agente orquestador: junta técnico + detección + noticias en un veredicto.

Este es el "cerebro" que combina las señales de los demás sub-agentes y
produce un puntaje de oportunidad y una recomendación en lenguaje natural.

⚠️ El resultado NO es asesoría financiera: es una señal para que TÚ decidas.
"""
from agente_inversion import indicadores
from agente_inversion.agentes import tecnico, deteccion, noticias


def evaluar(emisora: str, df, revisar_noticias: bool = True) -> dict:
    """Ejecuta todo el análisis para una emisora y devuelve un reporte."""
    df_ind = indicadores.calcular_todos(df)

    res_tecnico = tecnico.analizar(df_ind)
    res_deteccion = deteccion.detectar(df_ind)
    res_noticias = (
        noticias.obtener_noticias(emisora) if revisar_noticias
        else {"titulares": [], "sentimiento_total": 0, "sesgo": "n/a"}
    )

    # Puntaje combinado: técnico + noticias + peso extra a detección temprana.
    puntaje = res_tecnico["puntaje"] + res_noticias["sentimiento_total"]
    if res_deteccion["deteccion_temprana"]:
        # La detección temprana no dice dirección, pero sí "pon atención".
        puntaje += 1 if res_tecnico["puntaje"] >= 0 else -1

    recomendacion = _clasificar(puntaje, res_deteccion["deteccion_temprana"])

    return {
        "emisora": emisora,
        "precio": res_tecnico["precio"],
        "puntaje": puntaje,
        "recomendacion": recomendacion,
        "tecnico": res_tecnico,
        "deteccion": res_deteccion,
        "noticias": res_noticias,
    }


def _clasificar(puntaje: int, temprana: bool) -> str:
    """Traduce el puntaje a una etiqueta legible."""
    if puntaje >= 3:
        base = "🟢 OPORTUNIDAD (señales alcistas fuertes)"
    elif puntaje >= 1:
        base = "🟢 Interés alcista moderado"
    elif puntaje <= -3:
        base = "🔴 PRECAUCIÓN (señales bajistas fuertes)"
    elif puntaje <= -1:
        base = "🔴 Sesgo bajista moderado"
    else:
        base = "⚪ Neutral / sin señal clara"

    if temprana:
        base += "  ⚡ (movimiento inusual detectado — vigilar)"
    return base
