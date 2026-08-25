"""Agente de detección temprana: busca movimientos inusuales.

La idea es cachar cosas ANTES de que sean obvias: volumen atípico,
movimientos fuertes de precio, o rupturas de máximos recientes.
"""
import config


def detectar(df) -> dict:
    """Revisa el último dato en busca de señales tempranas."""
    ultima = df.iloc[-1]
    alertas = []
    temprana = False

    # --- Volumen inusual ---
    vol_rel = float(ultima["vol_rel"])
    if vol_rel >= config.VOLUMEN_INUSUAL_FACTOR:
        alertas.append(
            f"🔊 Volumen inusual: {vol_rel:.1f}x el promedio "
            "(alguien se está moviendo)"
        )
        temprana = True

    # --- Movimiento fuerte de precio ---
    cambio = float(ultima["cambio_pct"])
    if abs(cambio) >= config.MOVIMIENTO_FUERTE_PCT:
        signo = "▲" if cambio > 0 else "▼"
        alertas.append(f"{signo} Movimiento fuerte: {cambio:+.1f}% en el día")
        temprana = True

    # --- Ruptura de máximo/mínimo de 20 días ---
    maximo_20 = df["cierre"].iloc[-21:-1].max()
    minimo_20 = df["cierre"].iloc[-21:-1].min()
    if ultima["cierre"] > maximo_20:
        alertas.append("🚀 Ruptura: nuevo máximo de 20 días")
        temprana = True
    elif ultima["cierre"] < minimo_20:
        alertas.append("⚠️ Quiebre: nuevo mínimo de 20 días")
        temprana = True

    return {
        "deteccion_temprana": temprana,
        "alertas": alertas,
        "vol_rel": round(vol_rel, 1),
        "cambio_pct": round(cambio, 1),
    }
