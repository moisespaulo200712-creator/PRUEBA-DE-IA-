"""Notificador de alertas: consola siempre, Telegram si está configurado."""
import config


def _formatear(reporte: dict) -> str:
    """Convierte un reporte en texto legible."""
    t = reporte["tecnico"]
    d = reporte["deteccion"]
    n = reporte["noticias"]

    lineas = [
        f"📊 {reporte['emisora']}  —  ${reporte['precio']}",
        f"   {reporte['recomendacion']}  (puntaje: {reporte['puntaje']:+d})",
        f"   Técnico [{t['sesgo']}]  RSI={t['rsi']}",
    ]
    for s in t["senales"]:
        lineas.append(f"     • {s}")
    if d["alertas"]:
        lineas.append("   Detección temprana:")
        for a in d["alertas"]:
            lineas.append(f"     • {a}")
    if n["titulares"]:
        lineas.append(f"   Noticias [{n['sesgo']}]:")
        for tit in n["titulares"][:3]:
            lineas.append(f"     • {tit['titulo']}")
    return "\n".join(lineas)


def notificar(reporte: dict, solo_oportunidades: bool = False) -> None:
    """Muestra el reporte en consola (y Telegram si está configurado)."""
    if solo_oportunidades and abs(reporte["puntaje"]) < 1 and not \
            reporte["deteccion"]["deteccion_temprana"]:
        return

    texto = _formatear(reporte)
    print(texto)
    print("-" * 60)

    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        _enviar_telegram(texto)


def _enviar_telegram(texto: str) -> None:
    """Envía la alerta por Telegram (opcional)."""
    import requests
    try:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": config.TELEGRAM_CHAT_ID, "text": texto},
            timeout=15,
        )
    except Exception as e:  # no romper el flujo por una alerta fallida
        print(f"(No se pudo enviar Telegram: {e})")
