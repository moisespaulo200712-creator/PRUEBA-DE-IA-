"""Agente de panorama de mercado (usa DataBursatil).

Da una foto rápida del mercado ANTES de entrar al detalle por emisora:
  - Las mayores alzas y bajas del día (endpoint /top).
  - El sentimiento de las noticias reales del día (endpoint /noticias),
    calculado con el mismo diccionario de palabras que el agente de noticias.

Es contexto macro para que TÚ decidas con la foto completa, no una
recomendación. Requiere DATABURSATIL_TOKEN en .env; si no hay, se omite.
"""
import config
from agente_inversion.agentes.noticias import _sentimiento_texto
from agente_inversion.datos import databursatil


def panorama(top_n: int = 5, limite_noticias: int = 8) -> dict | None:
    """Arma el panorama del mercado. Devuelve None si no hay token o falla."""
    token = config.DATABURSATIL_TOKEN
    if not token:
        return None

    resultado: dict = {"top": None, "noticias": None}

    try:
        resultado["top"] = databursatil.obtener_top(token, cantidad=top_n)
    except Exception:
        resultado["top"] = None

    try:
        crudas = databursatil.obtener_noticias_api(token, limite=limite_noticias)
        noticias = []
        total = 0
        for it in crudas:
            titulo = it.get("n", "")
            cuerpo = it.get("c", "")
            s = _sentimiento_texto(f"{titulo} {cuerpo}")
            total += s
            noticias.append({"titulo": titulo, "sentimiento": s,
                             "link": it.get("f", "")})
        resultado["noticias"] = {
            "titulares": noticias,
            "sentimiento_total": total,
            "sesgo": "positivo" if total > 0 else "negativo" if total < 0 else "neutral",
        }
    except Exception:
        resultado["noticias"] = None

    if resultado["top"] is None and resultado["noticias"] is None:
        return None
    return resultado


def formatear(pan: dict) -> str:
    """Convierte el panorama en texto legible para la consola."""
    lineas = ["🌎 PANORAMA DEL MERCADO (BMV, datos DataBursatil)"]

    top = pan.get("top")
    if top:
        suben = top.get("SUBEN") or top.get("suben") or []
        bajan = top.get("BAJAN") or top.get("bajan") or []
        if suben:
            partes = ", ".join(f"{x['e']} ({x['c']:+.1f}%)" for x in suben[:5])
            lineas.append(f"   📈 Mayores alzas:  {partes}")
        if bajan:
            partes = ", ".join(f"{x['e']} ({x['c']:+.1f}%)" for x in bajan[:5])
            lineas.append(f"   📉 Mayores bajas:  {partes}")

    noti = pan.get("noticias")
    if noti and noti["titulares"]:
        lineas.append(f"   📰 Noticias del día [sesgo {noti['sesgo']}]:")
        for t in noti["titulares"][:4]:
            lineas.append(f"      • {t['titulo']}")

    return "\n".join(lineas)
