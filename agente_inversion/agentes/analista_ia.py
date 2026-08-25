"""Agente analista con IA (Claude): sintetiza todas las señales en un veredicto.

Toma los reportes técnicos + detección + noticias de todas las emisoras y le
pide a Claude que los interprete como lo haría un analista: explica el porqué,
prioriza oportunidades y advierte riesgos.

Requiere:
    pip install anthropic
    ANTHROPIC_API_KEY en tu archivo .env  (saca tu key en https://console.anthropic.com/)

⚠️ El análisis de Claude es informativo, NO es asesoría financiera.
"""
import os

# Modelo por defecto. Puedes cambiarlo (ej. "claude-opus-4-8" para más profundidad).
MODELO_DEFAULT = "claude-sonnet-5"

_SYSTEM = (
    "Eres un analista financiero que ayuda a un inversionista minorista en México "
    "(mercado BMV/BIVA). Recibes señales técnicas, detecciones de movimientos "
    "inusuales y titulares de noticias por emisora. Tu trabajo:\n"
    "1. Interpretar las señales en conjunto (no repetirlas: explicarlas).\n"
    "2. Priorizar 1-3 oportunidades con la razón concreta de cada una.\n"
    "3. Señalar riesgos claros y qué vigilar.\n"
    "Sé directo y breve. Usa español de México. SIEMPRE cierra recordando que "
    "esto es informativo, no asesoría financiera, y que la decisión es del usuario."
)


def _resumir_reportes(reportes: list[dict]) -> str:
    """Convierte los reportes en un texto compacto para el prompt."""
    bloques = []
    for r in reportes:
        t = r["tecnico"]
        d = r["deteccion"]
        n = r["noticias"]
        titulares = "; ".join(x["titulo"] for x in n.get("titulares", [])[:3]) or "sin titulares"
        bloques.append(
            f"- {r['emisora']} | precio ${r['precio']} | puntaje {r['puntaje']:+d} "
            f"| técnico: {t['sesgo']} (RSI {t['rsi']}) "
            f"| detección temprana: {'SÍ - ' + '; '.join(d['alertas']) if d['alertas'] else 'no'} "
            f"| noticias ({n['sesgo']}): {titulares}"
        )
    return "\n".join(bloques)


def analizar(reportes: list[dict], modelo: str = MODELO_DEFAULT) -> str:
    """Pide a Claude un análisis global de las emisoras evaluadas.

    Devuelve el texto del análisis, o un mensaje de ayuda si falta la API key
    o el paquete `anthropic`.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        return (
            "⚠️ No hay ANTHROPIC_API_KEY configurada. Para activar el análisis "
            "con Claude:\n"
            "  1) Saca tu key en https://console.anthropic.com/\n"
            "  2) Ponla en tu archivo .env como ANTHROPIC_API_KEY=sk-ant-...\n"
            "  3) pip install anthropic"
        )
    try:
        import anthropic
    except ImportError:
        return "⚠️ Falta el paquete 'anthropic'. Instálalo con: pip install anthropic"

    cliente = anthropic.Anthropic()
    resumen = _resumir_reportes(reportes)
    resp = cliente.messages.create(
        model=modelo,
        max_tokens=1200,
        system=_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                "Estas son las señales de hoy para las emisoras que vigilo. "
                "Dame tu análisis y las mejores oportunidades:\n\n" + resumen
            ),
        }],
    )
    return resp.content[0].text
