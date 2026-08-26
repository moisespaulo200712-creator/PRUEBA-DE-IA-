"""Agente de análisis FUNDAMENTAL (usa /financieros de DataBursatil).

Mientras el agente técnico mira el PRECIO, este mira el NEGOCIO: ¿la empresa
gana dinero? ¿crece? ¿tiene mucha deuda? Es lo que revisa un inversionista de
largo plazo antes de comprar.

Calcula los números que de verdad miran los expertos:
  - Margen neto      = utilidad / ingresos   (de cada peso que vende, ¿cuánto gana?)
  - Margen bruto     = utilidad bruta / ingresos
  - Crecimiento      = ingresos y utilidad de este año vs el anterior
  - ROE              = utilidad / capital     (retorno sobre el dinero de los dueños)
  - Razón de deuda   = pasivos / activos      (qué tan endeudada está)

⚠️ Es información para ANALIZAR, no una recomendación de compra/venta.
   Los bancos (GFNORTE, etc.) reportan distinto y pueden no traer estos campos.
"""
import config
from agente_inversion.datos import databursatil

# El endpoint /financieros usa la emisora SIN serie. Mapa para la watchlist.
TICKER_A_EMISORA = {
    "WALMEX": "WALMEX", "WALMEX*": "WALMEX",
    "GMEXICOB": "GMEXICO", "GMEXICO": "GMEXICO",
    "CEMEXCPO": "CEMEX", "CEMEX": "CEMEX",
    "GFNORTEO": "GFNORTE", "GFNORTE": "GFNORTE",
    "FEMSAUBD": "FEMSA", "FEMSA": "FEMSA",
    "AMXB": "AMX", "AMXL": "AMX", "AMX": "AMX",
    "ALSEA*": "ALSEA", "ALSEA": "ALSEA",
}


def _emisora_base(ticker: str) -> str:
    """Convierte un ticker (con serie) al nombre que usa /financieros."""
    t = ticker.strip().upper()
    if t.endswith(".MX"):
        t = t[:-3]
    return TICKER_A_EMISORA.get(t, t.rstrip("*"))


def _num(campo):
    """Extrae el número de un campo con forma ['etiqueta', valor]."""
    if isinstance(campo, (list, tuple)) and len(campo) >= 2:
        try:
            return float(campo[1])
        except (TypeError, ValueError):
            return None
    return None


def _ultimo_y_previo(periodos: dict):
    """Devuelve (periodo_reciente, periodo_anterior) ordenados por fecha."""
    claves = sorted(periodos.keys())
    if not claves:
        return None, None
    reciente = periodos[claves[-1]]
    previo = periodos[claves[-2]] if len(claves) >= 2 else None
    return reciente, previo


def obtener(ticker: str, periodo: str = "4T_2024") -> dict:
    """Descarga resultados (P&L) y posición (balance) de la emisora."""
    token = config.DATABURSATIL_TOKEN
    if not token:
        raise ValueError("Falta DATABURSATIL_TOKEN en .env")
    emisora = _emisora_base(ticker)

    def _pedir(tipo):
        try:
            d = databursatil._get_api(
                "financieros", token, emisora=emisora,
                periodo=periodo, financieros=tipo,
            )
        except Exception:
            # Bancos u otras emisoras reportan distinto -> 400. Se omite.
            return None
        if isinstance(d, dict) and "error" in d:
            return None
        # d = {tipo: {periodo: {campos}}}
        if isinstance(d, dict) and d:
            interno = list(d.values())[0]
            return interno if isinstance(interno, dict) else None
        return None

    return {
        "emisora": emisora,
        "resultado": _pedir("resultado_acumulado"),
        "posicion": _pedir("posicion"),
    }


def analizar(ticker: str, periodo: str = "4T_2024") -> dict:
    """Calcula los indicadores fundamentales y una lectura de salud."""
    datos = obtener(ticker, periodo)
    res = {"ticker": ticker, "emisora": datos["emisora"], "disponible": False,
           "notas": []}

    pnl = datos["resultado"]
    if not pnl:
        res["notas"].append(
            "Sin estados financieros estándar (¿banco o sin reporte?)."
        )
        return res

    reciente, previo = _ultimo_y_previo(pnl)
    if not reciente:
        return res

    ingresos = _num(reciente.get("revenue"))
    utilidad = _num(reciente.get("profitloss"))
    bruta = _num(reciente.get("grossprofit"))

    res["ingresos"] = ingresos
    res["utilidad_neta"] = utilidad
    res["margen_neto"] = _pct(utilidad, ingresos)
    res["margen_bruto"] = _pct(bruta, ingresos)

    # Crecimiento vs año anterior.
    if previo:
        ing_prev = _num(previo.get("revenue"))
        uti_prev = _num(previo.get("profitloss"))
        res["crecimiento_ingresos"] = _crecimiento(ingresos, ing_prev)
        res["crecimiento_utilidad"] = _crecimiento(utilidad, uti_prev)

    # Balance: deuda y ROE.
    bal = datos["posicion"]
    if bal:
        _, = (None,)  # noqa
        reciente_bal, _ = _ultimo_y_previo(bal)
        if reciente_bal:
            activos = _num(reciente_bal.get("assets"))
            pasivos = _num(reciente_bal.get("liabilities"))
            capital = _num(reciente_bal.get("equity"))
            res["razon_deuda"] = _ratio(pasivos, activos)
            res["roe"] = _pct(utilidad, capital)

    res["disponible"] = True
    res["salud"] = _leer_salud(res)
    return res


def _pct(a, b):
    if a is None or b in (None, 0):
        return None
    return round(a / b * 100, 1)


def _ratio(a, b):
    if a is None or b in (None, 0):
        return None
    return round(a / b, 2)


def _crecimiento(actual, previo):
    if actual is None or previo in (None, 0):
        return None
    return round((actual - previo) / abs(previo) * 100, 1)


def _leer_salud(r: dict) -> list[str]:
    """Traduce los números a frases informativas (no recomendaciones)."""
    notas = []
    mn = r.get("margen_neto")
    if mn is not None:
        if mn <= 0:
            notas.append("🔴 Está perdiendo dinero (margen neto negativo)")
        elif mn >= 10:
            notas.append(f"🟢 Muy rentable: gana {mn}¢ por cada peso vendido")
        else:
            notas.append(f"🟡 Rentabilidad moderada: {mn}% de margen neto")

    ci = r.get("crecimiento_ingresos")
    if ci is not None:
        if ci > 0:
            notas.append(f"🟢 Ventas creciendo {ci}% vs año anterior")
        else:
            notas.append(f"🔴 Ventas cayendo {ci}% vs año anterior")

    rd = r.get("razon_deuda")
    if rd is not None:
        if rd < 0.5:
            notas.append(f"🟢 Deuda controlada ({int(rd*100)}% de sus activos)")
        elif rd <= 0.7:
            notas.append(f"🟡 Deuda moderada ({int(rd*100)}% de sus activos)")
        else:
            notas.append(f"🔴 Deuda alta ({int(rd*100)}% de sus activos)")

    roe = r.get("roe")
    if roe is not None:
        if roe >= 15:
            notas.append(f"🟢 Buen retorno al capital (ROE {roe}%)")
        elif roe > 0:
            notas.append(f"🟡 Retorno al capital moderado (ROE {roe}%)")
    return notas


def _dinero(n) -> str:
    """Formatea un monto grande en miles de millones (mmdp) o millones."""
    if n is None:
        return "—"
    if abs(n) >= 1e9:
        return f"${n/1e9:,.1f} mmdp"   # miles de millones de pesos
    if abs(n) >= 1e6:
        return f"${n/1e6:,.1f} mdp"
    return f"${n:,.0f}"


def formatear(res: dict) -> str:
    """Reporte fundamental legible para consola."""
    if not res.get("disponible"):
        nota = res["notas"][0] if res.get("notas") else "sin datos"
        return f"🏢 {res['emisora']} (fundamental): {nota}"

    L = [
        f"🏢 FUNDAMENTAL: {res['emisora']}",
        f"   Ingresos: {_dinero(res.get('ingresos'))}   "
        f"Utilidad neta: {_dinero(res.get('utilidad_neta'))}",
        f"   Margen neto: {_fmt(res.get('margen_neto'),'%')}   "
        f"Margen bruto: {_fmt(res.get('margen_bruto'),'%')}",
    ]
    if res.get("crecimiento_ingresos") is not None:
        L.append(
            f"   Crecimiento ventas: {_fmt(res.get('crecimiento_ingresos'),'%',True)}   "
            f"utilidad: {_fmt(res.get('crecimiento_utilidad'),'%',True)}"
        )
    if res.get("razon_deuda") is not None:
        L.append(
            f"   Razón de deuda: {res.get('razon_deuda')}   "
            f"ROE: {_fmt(res.get('roe'),'%')}"
        )
    L.append("   Lectura:")
    for n in res.get("salud", []):
        L.append(f"     • {n}")
    return "\n".join(L)


def _fmt(v, suf="", signo=False):
    if v is None:
        return "—"
    s = f"{'+' if signo and v > 0 else ''}{v}{suf}"
    return s
