"""Agente técnico: convierte los indicadores en señales legibles."""
import config


def analizar(df) -> dict:
    """Analiza el último dato disponible y devuelve señales.

    Devuelve un dict con: señales (lista), sesgo (+/-) y detalle numérico.
    """
    ultima = df.iloc[-1]
    senales = []
    puntaje = 0  # positivo = alcista, negativo = bajista

    # --- RSI ---
    rsi_val = ultima["rsi"]
    if rsi_val <= config.RSI_SOBREVENTA:
        senales.append(f"RSI en sobreventa ({rsi_val:.0f}) → posible rebote")
        puntaje += 1
    elif rsi_val >= config.RSI_SOBRECOMPRA:
        senales.append(f"RSI en sobrecompra ({rsi_val:.0f}) → posible corrección")
        puntaje -= 1

    # --- Cruce de medias (tendencia) ---
    if ultima["sma20"] > ultima["sma50"]:
        senales.append("Media 20 por encima de la 50 → tendencia alcista")
        puntaje += 1
    else:
        senales.append("Media 20 por debajo de la 50 → tendencia bajista")
        puntaje -= 1

    # --- MACD ---
    if ultima["macd"] > ultima["macd_senal"]:
        senales.append("MACD por encima de su señal → momentum positivo")
        puntaje += 1
    else:
        senales.append("MACD por debajo de su señal → momentum negativo")
        puntaje -= 1

    # --- Bollinger ---
    if ultima["cierre"] <= ultima["bb_inf"]:
        senales.append("Precio en banda inferior de Bollinger → posible piso")
        puntaje += 1
    elif ultima["cierre"] >= ultima["bb_sup"]:
        senales.append("Precio en banda superior de Bollinger → posible techo")
        puntaje -= 1

    return {
        "puntaje": puntaje,
        "sesgo": "alcista" if puntaje > 0 else "bajista" if puntaje < 0 else "neutral",
        "senales": senales,
        "rsi": round(float(rsi_val), 1),
        "precio": round(float(ultima["cierre"]), 2),
    }
