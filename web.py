"""Dashboard web del Agente de Inversión — estilo terminal de casa de bolsa.

Sirve una página que se auto-actualiza con:
  - Estado del mercado (abierto/cerrado) según el horario de la BMV
  - Panorama: mayores alzas/bajas del día + noticias reales (DataBursatil)
  - Tarjetas por emisora: precio, cambio, RSI con etiqueta sobrecompra/venta,
    señales, alertas y una mini-gráfica (sparkline) de los últimos días

Uso:
    python web.py
    # abre http://localhost:8000

⚠️ Herramienta de análisis. NO es asesoría financiera. La decisión es tuya.
"""
import time
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, render_template_string, request

import config
from agente_inversion import indicadores
from agente_inversion.datos import obtener_proveedor, databursatil
from agente_inversion.agentes import oportunidades, mercado

app = Flask(__name__)

WATCHLIST_DEFAULT = ["GMEXICOB", "CEMEXCPO", "WALMEX*", "GFNORTEO", "FEMSAUBD", "AMXB"]

_TZ = ZoneInfo("America/Mexico_City")
# Horario regular de la BMV (hora de la Ciudad de México).
_APERTURA = dtime(8, 30)
_CIERRE = dtime(15, 0)

_cache: dict = {}


def _cacheado(clave: str, segundos: int, funcion):
    ahora = time.time()
    e = _cache.get(clave)
    if e and (ahora - e["t"]) < segundos:
        return e["v"]
    v = funcion()
    _cache[clave] = {"t": ahora, "v": v}
    return v


def _estado_mercado() -> dict:
    """Calcula si la BMV está abierta y a qué hora abre/cierra."""
    ahora = datetime.now(_TZ)
    es_habil = ahora.weekday() < 5  # 0-4 = lun-vie
    hora = ahora.time()
    abierto = es_habil and _APERTURA <= hora < _CIERRE
    if abierto:
        estado, detalle = "ABIERTO", f"Cierra a las {_CIERRE.strftime('%H:%M')}"
    elif es_habil and hora < _APERTURA:
        estado, detalle = "CERRADO", f"Abre a las {_APERTURA.strftime('%H:%M')}"
    elif es_habil:
        estado, detalle = "CERRADO", "Abre mañana 08:30"
    else:
        estado, detalle = "CERRADO", "Fin de semana · abre lunes 08:30"
    return {
        "estado": estado,
        "detalle": detalle,
        "hora": ahora.strftime("%H:%M:%S"),
        "fecha": ahora.strftime("%a %d %b %Y"),
    }


def _cotizaciones(tickers: list[str]) -> dict:
    token = config.DATABURSATIL_TOKEN
    if not token:
        return {}
    try:
        datos = databursatil._get_api(
            "cotizaciones", token,
            emisora_serie=",".join(tickers), bolsa="BMV", concepto="U,C",
        )
    except Exception:
        return {}
    salida = {}

    def _recorrer(d):
        for k, v in (d.items() if isinstance(d, dict) else []):
            if isinstance(v, dict) and ("U" in v or "u" in v):
                salida[k] = {"ultimo": v.get("U", v.get("u")),
                             "cambio": v.get("C", v.get("c"))}
            elif isinstance(v, dict):
                _recorrer(v)

    _recorrer(datos)
    return salida


def _rsi_estado(rsi: float) -> str:
    if rsi >= config.RSI_SOBRECOMPRA:
        return "sobrecompra"
    if rsi <= config.RSI_SOBREVENTA:
        return "sobreventa"
    return "normal"


@app.route("/")
def index():
    return render_template_string(_HTML)


@app.route("/api/estado")
def api_estado():
    return jsonify(_estado_mercado())


@app.route("/api/panorama")
def api_panorama():
    return jsonify(_cacheado("panorama", 60, lambda: mercado.panorama() or {}))


@app.route("/api/emisoras")
def api_emisoras():
    tickers = request.args.get("tickers", "")
    lista = [t.strip() for t in tickers.split(",") if t.strip()] or WATCHLIST_DEFAULT
    proveedor = obtener_proveedor("databursatil")

    def _analizar():
        out = []
        for t in lista:
            try:
                df = proveedor.historico(t, dias=180)
                rep = oportunidades.evaluar(t, df, revisar_noticias=False)
                cierres = [round(float(x), 2) for x in df["cierre"].tail(40)]
                out.append({
                    "emisora": rep["emisora"],
                    "precio": rep["precio"],
                    "puntaje": rep["puntaje"],
                    "recomendacion": rep["recomendacion"],
                    "sesgo": rep["tecnico"]["sesgo"],
                    "rsi": rep["tecnico"]["rsi"],
                    "rsi_estado": _rsi_estado(rep["tecnico"]["rsi"]),
                    "senales": rep["tecnico"]["senales"],
                    "alertas": rep["deteccion"]["alertas"],
                    "temprana": rep["deteccion"]["deteccion_temprana"],
                    "historia": cierres,
                })
            except Exception as e:
                out.append({"emisora": t, "error": str(e)})
        return out

    clave = "emisoras:" + ",".join(lista)
    reportes = _cacheado(clave, 300, _analizar)

    cots = _cacheado("cot:" + ",".join(lista), 30, lambda: _cotizaciones(lista))
    for r in reportes:
        c = cots.get(r.get("emisora"))
        if c:
            r["live_precio"] = c["ultimo"]
            r["live_cambio"] = c["cambio"]

    reportes.sort(key=lambda r: r.get("puntaje", -99), reverse=True)
    return jsonify(reportes)


_HTML = r"""
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agente de Inversión — Terminal BMV</title>
<style>
  :root{
    --bg:#0a0d13; --panel:#111722; --panel2:#0f1520; --line:#1e2836;
    --txt:#e8eef6; --muted:#7d8ba0; --up:#26d07c; --down:#ff5a5f;
    --accent:#4c9aff; --gold:#f5c451; --chip:#1a2330;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,sans-serif;
    -webkit-font-smoothing:antialiased}
  .topbar{display:flex;align-items:center;justify-content:space-between;
    padding:12px 20px;background:linear-gradient(180deg,#0e1420,#0a0d13);
    border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10;flex-wrap:wrap;gap:10px}
  .brand{display:flex;align-items:center;gap:10px}
  .brand h1{font-size:16px;margin:0;letter-spacing:.3px}
  .brand .tag{font-size:10px;color:var(--muted);border:1px solid var(--line);
    padding:2px 6px;border-radius:5px}
  .status{display:flex;align-items:center;gap:14px;font-size:12px}
  .mkt{display:flex;align-items:center;gap:7px;font-weight:600}
  .dot{width:9px;height:9px;border-radius:50%;box-shadow:0 0 8px currentColor}
  .open{color:var(--up)} .closed{color:var(--down)}
  .clock{font-variant-numeric:tabular-nums;color:var(--txt);font-weight:600}
  .muted{color:var(--muted)}
  .disc{background:#231d09;border-bottom:1px solid #3d3413;color:var(--gold);
    padding:7px 20px;font-size:12px;text-align:center}
  .wrap{padding:18px 20px;max-width:1200px;margin:0 auto}
  .row{display:grid;grid-template-columns:1.1fr 1fr;gap:14px;margin-bottom:18px}
  @media(max-width:820px){.row{grid-template-columns:1fr}}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
  .card h2{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin:0 0 12px}
  .movers-row{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px}
  .chip{background:var(--chip);border:1px solid var(--line);border-radius:7px;
    padding:4px 9px;font-size:12px;font-variant-numeric:tabular-nums;white-space:nowrap}
  .up{color:var(--up)} .down{color:var(--down)}
  .news{list-style:none;padding:0;margin:0}
  .news li{font-size:13px;padding:6px 0;border-bottom:1px solid var(--panel2);line-height:1.4}
  .news a{color:var(--txt);text-decoration:none}
  .news a:hover{color:var(--accent)}
  .sec-title{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin:6px 0 12px}
  .cards{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  @media(max-width:820px){.cards{grid-template-columns:1fr}}
  .emi{background:var(--panel);border:1px solid var(--line);border-radius:14px;
    padding:16px;position:relative;overflow:hidden;transition:border-color .2s}
  .emi:hover{border-color:#2c3a4f}
  .emi.strong{border-color:#1c4d33}
  .emi-head{display:flex;justify-content:space-between;align-items:flex-start}
  .emi-name{font-size:18px;font-weight:700;letter-spacing:.3px}
  .emi-price{font-size:20px;font-weight:700;font-variant-numeric:tabular-nums;text-align:right}
  .emi-chg{font-size:13px;font-weight:600;font-variant-numeric:tabular-nums}
  .spark{margin:10px 0 6px}
  .badges{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0}
  .b{font-size:10px;font-weight:700;letter-spacing:.4px;padding:3px 8px;border-radius:20px;text-transform:uppercase}
  .b-green{background:#0f3323;color:var(--up)} .b-red{background:#3a1618;color:var(--down)}
  .b-gray{background:#1a2330;color:var(--muted)}
  .b-hot{background:#3a2a0c;color:var(--gold)}
  .b-over{background:#3a1618;color:#ffb0b3} .b-under{background:#0f3323;color:#7ff0bb}
  .rsi-wrap{margin:8px 0}
  .rsi-bar{height:6px;background:#1a2330;border-radius:4px;position:relative;overflow:hidden}
  .rsi-fill{height:100%;border-radius:4px}
  .rsi-lbl{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-top:3px}
  .sig{font-size:12px;color:#c3cdda;margin-top:4px;line-height:1.5}
  .sig .al{color:var(--gold)}
  .foot{display:flex;justify-content:space-between;align-items:center;margin-top:20px;
    padding-top:14px;border-top:1px solid var(--line);font-size:11px;color:var(--muted)}
  .gbm{color:var(--accent);text-decoration:none;font-weight:600}
  .refresh{font-size:11px;color:var(--muted)}
</style>
</head>
<body>
<div class="topbar">
  <div class="brand">
    <h1>📈 Agente de Inversión</h1>
    <span class="tag">TERMINAL BMV</span>
  </div>
  <div class="status">
    <div class="mkt" id="mkt"><span class="dot closed">●</span><span>—</span></div>
    <div class="muted" id="mkt-detail">—</div>
    <div class="clock" id="clock">--:--:--</div>
    <div class="refresh">↻ <span id="cd">–</span>s</div>
  </div>
</div>
<div class="disc">⚠️ Análisis informativo, <b>no es asesoría financiera</b>. Qué compras, cuándo y cuánto es tu decisión y tu riesgo. Operar se hace en tu casa de bolsa.</div>

<div class="wrap">
  <div class="row">
    <div class="card">
      <h2>🌎 Panorama del mercado</h2>
      <div class="muted" style="font-size:11px;margin-bottom:4px">Mayores alzas</div>
      <div class="movers-row" id="suben"><span class="chip muted">Cargando…</span></div>
      <div class="muted" style="font-size:11px;margin:8px 0 4px">Mayores bajas</div>
      <div class="movers-row" id="bajan"></div>
    </div>
    <div class="card">
      <h2>📰 Noticias del día</h2>
      <ul class="news" id="news"><li class="muted">Cargando…</li></ul>
    </div>
  </div>

  <div class="sec-title">📊 Tu watchlist · ordenada por señal</div>
  <div class="cards" id="cards"><div class="muted">Analizando con datos reales de la BMV…</div></div>

  <div class="foot">
    <div>Datos: DataBursatil · Análisis: técnico + detección</div>
    <div>Operar en <a class="gbm" href="https://gbm.com/" target="_blank">GBM ↗</a></div>
  </div>
</div>

<script>
const REFRESH=60; let cd=REFRESH;

function chg(c){ if(c==null) return "";
  const cls=c>=0?"up":"down", s=c>=0?"▲ +":"▼ ";
  return `<span class="${cls}">${s}${Math.abs(Number(c)).toFixed(2)}%</span>`; }

function sparkline(data){
  if(!data||data.length<2) return "";
  const w=100,h=28,min=Math.min(...data),max=Math.max(...data),rng=(max-min)||1;
  const pts=data.map((v,i)=>`${(i/(data.length-1)*w).toFixed(1)},${(h-(v-min)/rng*h).toFixed(1)}`).join(" ");
  const rising=data[data.length-1]>=data[0];
  const col=rising?"var(--up)":"var(--down)";
  return `<svg class="spark" width="100%" height="28" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
    <polyline points="${pts}" fill="none" stroke="${col}" stroke-width="1.6"/></svg>`;
}

async function loadEstado(){
  try{ const s=await (await fetch("/api/estado")).json();
    const abierto=s.estado==="ABIERTO";
    document.getElementById("mkt").innerHTML=
      `<span class="dot ${abierto?'open':'closed'}">●</span><span class="${abierto?'open':'closed'}">MERCADO ${s.estado}</span>`;
    document.getElementById("mkt-detail").textContent=s.detalle+" · "+s.fecha;
    document.getElementById("clock").textContent=s.hora;
  }catch(e){}
}

async function loadPanorama(){
  try{ const p=await (await fetch("/api/panorama")).json();
    const top=p.top||{}, su=top.SUBEN||top.suben||[], ba=top.BAJAN||top.bajan||[];
    document.getElementById("suben").innerHTML= su.length?
      su.slice(0,6).map(x=>`<span class="chip"><b>${x.e}</b> ${chg(x.c)}</span>`).join(""):'<span class="chip muted">—</span>';
    document.getElementById("bajan").innerHTML= ba.length?
      ba.slice(0,6).map(x=>`<span class="chip"><b>${x.e}</b> ${chg(x.c)}</span>`).join(""):'<span class="chip muted">—</span>';
    const noti=(p.noticias&&p.noticias.titulares)||[];
    document.getElementById("news").innerHTML= noti.length?
      noti.slice(0,6).map(t=>`<li>${t.link?`<a href="${t.link}" target="_blank">`:""}${t.titulo}${t.link?" ↗</a>":""}</li>`).join(""):'<li class="muted">Sin noticias ahora.</li>';
  }catch(e){}
}

async function loadEmisoras(){
  try{ const arr=await (await fetch("/api/emisoras")).json();
    document.getElementById("cards").innerHTML=arr.map(e=>{
      if(e.error) return `<div class="emi"><div class="emi-name">${e.emisora}</div><div class="sig">⚠️ ${e.error}</div></div>`;
      const strong=e.puntaje>=3;
      const sBadge=e.puntaje>=1?"b-green":e.puntaje<=-1?"b-red":"b-gray";
      const sTxt=e.puntaje>=1?"Alcista":e.puntaje<=-1?"Bajista":"Neutral";
      const price=e.live_precio!=null?e.live_precio:e.precio;
      const chgHtml=e.live_cambio!=null?`<div class="emi-chg">${chg(e.live_cambio)}</div>`:"";
      // RSI bar
      const rsi=e.rsi, rsiCol= rsi>=70?"var(--down)":rsi<=30?"var(--up)":"var(--accent)";
      let rsiBadge="";
      if(e.rsi_estado==="sobrecompra") rsiBadge='<span class="b b-over">Sobrecompra</span>';
      else if(e.rsi_estado==="sobreventa") rsiBadge='<span class="b b-under">Sobreventa</span>';
      const hot=e.temprana?'<span class="b b-hot">⚡ Movimiento inusual</span>':"";
      const señales=(e.senales||[]).map(s=>`<div>· ${s}</div>`).join("");
      const alertas=(e.alertas||[]).map(a=>`<div class="al">⚡ ${a}</div>`).join("");
      return `<div class="emi ${strong?'strong':''}">
        <div class="emi-head">
          <div><div class="emi-name">${e.emisora}</div>
            <div class="muted" style="font-size:11px">Puntaje ${e.puntaje>=0?"+":""}${e.puntaje} · ${e.sesgo}</div>
          </div>
          <div><div class="emi-price">$${price}</div>${chgHtml}</div>
        </div>
        ${sparkline(e.historia)}
        <div class="badges"><span class="b ${sBadge}">${sTxt}</span>${rsiBadge}${hot}</div>
        <div class="rsi-wrap">
          <div class="rsi-bar"><div class="rsi-fill" style="width:${Math.min(rsi,100)}%;background:${rsiCol}"></div></div>
          <div class="rsi-lbl"><span>RSI ${rsi}</span><span>0 · 30 · 70 · 100</span></div>
        </div>
        <div class="sig">${señales}${alertas}</div>
      </div>`;
    }).join("");
  }catch(e){}
}

function refrescar(){ loadEstado(); loadPanorama(); loadEmisoras(); }
function tick(){ cd--; document.getElementById("cd").textContent=cd;
  loadEstado(); // el reloj y estado se refrescan cada segundo
  if(cd<=0){ cd=REFRESH; loadPanorama(); loadEmisoras(); } }
refrescar(); setInterval(tick,1000);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    print("=" * 60)
    print("  Terminal del Agente de Inversión")
    print("  Abre en tu navegador:  http://localhost:8000")
    print("  ⚠️  Análisis informativo. No es asesoría financiera.")
    print("=" * 60)
    app.run(host="127.0.0.1", port=8000, debug=False)
