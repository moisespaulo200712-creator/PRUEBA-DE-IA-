"""Agente de noticias: lee RSS de medios financieros MX y estima sentimiento.

De momento usa un sentimiento sencillo por palabras clave (sin costo).
Hay un hook `analizar_con_llm` por si luego quieres conectar Claude/OpenAI
para un análisis mucho más fino.
"""
import config

# Palabras clave para un sentimiento básico (rápido y gratis).
_POSITIVAS = {
    "sube", "gana", "ganancias", "récord", "record", "alza", "crece",
    "crecimiento", "supera", "optimismo", "rebote", "acuerdo", "utilidad",
    "avanza", "máximo", "maximo", "dividendo",
}
_NEGATIVAS = {
    "cae", "baja", "pierde", "pérdidas", "perdidas", "desploma", "crisis",
    "recesión", "recesion", "inflación", "inflacion", "riesgo", "temor",
    "recorte", "quiebra", "mínimo", "minimo", "sanción", "sancion",
}


def _sentimiento_texto(texto: str) -> int:
    t = texto.lower()
    pos = sum(1 for p in _POSITIVAS if p in t)
    neg = sum(1 for n in _NEGATIVAS if n in t)
    return pos - neg


def obtener_noticias(emisora: str | None = None, limite: int = 8) -> dict:
    """Descarga titulares de las fuentes RSS y estima el sentimiento.

    Si se pasa `emisora`, filtra titulares que la mencionen (por nombre
    corto). Devuelve titulares + un puntaje agregado de sentimiento.
    """
    try:
        import feedparser
    except ImportError as e:  # pragma: no cover
        raise ImportError("Falta feedparser. Instálalo: pip install feedparser") from e

    titulares = []
    for url in config.FUENTES_RSS:
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue
        for entrada in feed.entries[:limite]:
            titulo = entrada.get("title", "")
            if emisora:
                clave = emisora.split(".")[0].lower()
                if clave not in titulo.lower():
                    continue
            titulares.append(
                {"titulo": titulo, "sentimiento": _sentimiento_texto(titulo),
                 "link": entrada.get("link", "")}
            )

    total = sum(t["sentimiento"] for t in titulares)
    return {
        "titulares": titulares[:limite],
        "sentimiento_total": total,
        "sesgo": "positivo" if total > 0 else "negativo" if total < 0 else "neutral",
    }


def analizar_con_llm(titulares: list[str]) -> str:
    """HOOK opcional: análisis de sentimiento con un LLM (Claude/OpenAI).

    Deja tu implementación aquí cuando quieras un análisis más profundo.
    Ejemplo con la API de Anthropic:

        import anthropic
        cliente = anthropic.Anthropic()
        resp = cliente.messages.create(
            model="claude-sonnet-5",
            max_tokens=500,
            messages=[{"role": "user", "content":
                "Analiza el sentimiento de estos titulares para inversión "
                "en la BMV y resume oportunidades:\n" + "\n".join(titulares)}],
        )
        return resp.content[0].text
    """
    return "(Hook de LLM no configurado — usando sentimiento por palabras clave.)"
