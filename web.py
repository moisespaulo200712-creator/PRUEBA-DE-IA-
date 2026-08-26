"""Dashboard web del Agente de Inversión (localhost).

Sirve una página que se auto-actualiza con:
  - Panorama del mercado (alzas/bajas + noticias reales de DataBursatil)
  - Señales por emisora (técnico + detección) de tu watchlist
  - Precio y cambio del día "casi en tiempo real" (endpoint /cotizaciones)

Uso:
    python web.py
    # luego abre http://localhost:5000 en tu navegador

⚠️ Herramienta de análisis. NO es asesoría financiera. La decisión es tuya.
"""
import time
from flask import Flask, jsonify, render_template_string, request

import config
from agente_inversion.datos import obtener_proveedor
from agente_inversion.datos import databursatil
from agente_inversion.agentes import oportunidades, mercado

app = Flask(__name__)

# Watchlist por defecto (formato DataBursatil, con serie).
WATCHLIST_DEFAULT = ["GMEXICOB", "CEMEXCPO", "WALMEX*", "GFNORTEO", "FEMSAUBD", "AMXB"]

# Caché simple para no gastar créditos de más ni recalcular a cada segundo.
_cache: dict = {}


def _cacheado(clave: str, segundos: int, funcion):
    """Devuelve el valor cacheado si está fresco; si no, lo recalcula."""
    ahora = time.time()
    entrada = _cache.get(clave)
    if entrada and (ahora - entrada["t"]) < segundos:
        return entrada["v"]
    valor = funcion()
    _cache[clave] = {"t": ahora, "v": valor}
    return valor


def _cotizaciones(tickers: list[str]) -> dict:
    """Precio último y cambio% del día por emisora (near real-time)."""
    token = config.DATABURSATIL_TOKEN
    if not token:
        return {}
    try:
        emisora_serie = ",".join(tickers)
        datos = databursatil._get_api(
            "cotizaciones", token,
            emisora_serie=emisora_serie, bolsa="BMV", concepto="U,C",
        )
    except Exception:
        return {}
    # Respuesta típica: {"BMV": {"GMEXICOB": {"U": .., "C": ..}, ...}} o similar.
    salida = {}
    def _recorrer(d):
        for k, v in (d.items() if isinstance(d, dict) else []):
            if isinstance(v, dict) and ("U" in v or "u" in v):
                salida[k] = {
                    "ultimo": v.get("U", v.get("u")),
                    "cambio": v.get("C", v.get("c")),
                }
            elif isinstance(v, dict):
                _recorrer(v)
    _recorrer(datos)
    return salida


@app.route("/")
def index():
    return render_template_string(_HTML)


@app.route("/api/panorama")
def api_panorama():
    """Panorama de mercado (cache 60s)."""
    pan = _cacheado("panorama", 60, lambda: mercado.panorama() or {})
    return jsonify(pan)


@app.route("/api/emisoras")
def api_emisoras():
    """Señales por emisora (técnico+detección, cache 5 min) + precio live (30s)."""
    tickers = request.args.get("tickers", "")
    lista = [t.strip() for t in tickers.split(",") if t.strip()] or WATCHLIST_DEFAULT

    proveedor = obtener_proveedor("databursatil")

    def _analizar():
        out = []
        for t in lista:
            try:
                df = proveedor.historico(t, dias=180)
                rep = oportunidades.evaluar(t, df, revisar_noticias=False)
                out.append({
                    "emisora": rep["emisora"],
                    "precio": rep["precio"],
                    "puntaje": rep["puntaje"],
                    "recomendacion": rep["recomendacion"],
                    "sesgo": rep["tecnico"]["sesgo"],
                    "rsi": rep["tecnico"]["rsi"],
                    "senales": rep["tecnico"]["senales"],
                    "alertas": rep["deteccion"]["alertas"],
                    "temprana": rep["deteccion"]["deteccion_temprana"],
                })
            except Exception as e:
                out.append({"emisora": t, "error": str(e)})
        return out

    clave = "emisoras:" + ",".join(lista)
    reportes = _cacheado(clave, 300, _analizar)

    # Precio live (más frecuente, no depende del cálculo pesado).
    cots = _cacheado("cot:" + ",".join(lista), 30, lambda: _cotizaciones(lista))
    for r in reportes:
        c = cots.get(r.get("emisora"))
        if c:
            r["live_precio"] = c["ultimo"]
            r["live_cambio"] = c["cambio"]

    # Orden por puntaje (mejores arriba).
    reportes.sort(key=lambda r: r.get("puntaje", -99), reverse=True)
    return jsonify(reportes)


_HTML = r"""
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agente de Inversión — Dashboard</title>
<style>
  :root {
    --bg:#0b0e14; --panel:#141a24; --panel2:#1b2230; --txt:#e6edf3;
    --muted:#8b98a9; --up:#2ecc71; --down:#ff5c5c; --accent:#4c9aff;
    --border:#232c3b; --yellow:#f5c451;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--txt);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  header { padding:18px 22px; border-bottom:1px solid var(--border);
    display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; }
  h1 { font-size:18px; margin:0; }
  .sub { color:var(--muted); font-size:12px; }
  .wrap { padding:18px 22px; max-width:1100px; margin:0 auto; }
  .disc { background:#2a2410; border:1px solid #4a3f14; color:var(--yellow);
    padding:8px 12px; border-radius:8px; font-size:12px; margin-bottom:16px; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
  @media (max-width:760px){ .grid{ grid-template-columns:1fr; } }
  .card { background:var(--panel); border:1px solid var(--border);
    border-radius:12px; padding:14px 16px; }
  .card h2 { font-size:13px; text-transform:uppercase; letter-spacing:.5px;
    color:var(--muted); margin:0 0 10px; }
  .movers span { display:inline-block; margin:2px 8px 2px 0; font-size:13px; }
  .up { color:var(--up); } .down { color:var(--down); }
  .news li { font-size:13px; margin-bottom:6px; color:#cfd8e3; }
  .news a { color:var(--accent); text-decoration:none; }
  .emi { background:var(--panel2); border:1px solid var(--border); border-radius:12px;
    padding:14px 16px; margin-bottom:12px; }
  .emi-top { display:flex; justify-content:space-between; align-items:baseline; }
  .emi-name { font-size:16px; font-weight:600; }
  .emi-price { font-size:15px; }
  .badge { font-size:11px; padding:2px 8px; border-radius:20px; margin-left:8px; }
  .b-green { background:#123723; color:var(--up); }
  .b-red { background:#3a1516; color:var(--down); }
  .b-gray { background:#232c3b; color:var(--muted); }
  .sig { font-size:12px; color:#cfd8e3; margin-top:6px; }
  .sig div { margin:2px 0; }
  .alert { color:var(--yellow); }
  .pill { font-size:11px; color:var(--muted); }
  .flash { animation:fl 1s ease; }
  @keyframes fl { from{ background:#1d2b1f; } to{ background:var(--panel2); } }
  footer { text-align:center; color:var(--muted); font-size:11px; padding:20px; }
</style>
</head>
<body>
<header>
  <div>
    <h1>📈 Agente de Inversión — BMV</h1>
    <div class="sub">Actualiza solo · datos DataBursatil · <span id="reloj"></span></div>
  </div>
  <div class="sub">Auto-refresh: <span id="cd">–</span>s</div>
</header>
<div class="wrap">
  <div class="disc">⚠️ Herramienta de análisis, <b>no es asesoría financiera</b>. Qué compras, cuándo y cuánto es tu decisión y tu riesgo.</div>

  <div class="grid">
    <div class="card">
      <h2>🌎 Panorama del mercado</h2>
      <div id="movers" class="movers"><div class="pill">Cargando…</div></div>
    </div>
    <div class="card">
      <h2>📰 Noticias del día</h2>
      <ul id="news" class="news"><li class="pill">Cargando…</li></ul>
    </div>
  </div>

  <h2 style="font-size:13px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin:22px 0 10px;">📊 Tu watchlist</h2>
  <div id="emisoras"><div class="pill">Cargando análisis…</div></div>
</div>
<footer>Agente de Inversión · localhost · uso informativo</footer>

<script>
const REFRESH = 60; // segundos
let cd = REFRESH;

function fmtCambio(c){
  if(c===undefined||c===null) return "";
  const cls = c>=0 ? "up" : "down";
  const s = c>=0 ? "+" : "";
  return `<span class="${cls}">${s}${Number(c).toFixed(2)}%</span>`;
}

async function cargarPanorama(){
  try{
    const r = await fetch("/api/panorama"); const p = await r.json();
    const m = document.getElementById("movers");
    let html = "";
    const top = p.top || {};
    const suben = top.SUBEN || top.suben || [];
    const bajan = top.BAJAN || top.bajan || [];
    if(suben.length){
      html += "<div>📈 Alzas: " + suben.slice(0,5).map(x=>`<span class="up">${x.e} ${fmtCambio(x.c)}</span>`).join("") + "</div>";
    }
    if(bajan.length){
      html += "<div>📉 Bajas: " + bajan.slice(0,5).map(x=>`<span class="down">${x.e} ${fmtCambio(x.c)}</span>`).join("") + "</div>";
    }
    m.innerHTML = html || '<div class="pill">Sin datos de mercado ahora.</div>';

    const news = document.getElementById("news");
    const noti = (p.noticias && p.noticias.titulares) || [];
    news.innerHTML = noti.length
      ? noti.slice(0,6).map(t=>`<li>${t.link?`<a href="${t.link}" target="_blank">`:""}${t.titulo}${t.link?"</a>":""}</li>`).join("")
      : '<li class="pill">Sin noticias ahora.</li>';
  }catch(e){ console.error(e); }
}

async function cargarEmisoras(){
  try{
    const r = await fetch("/api/emisoras"); const arr = await r.json();
    const cont = document.getElementById("emisoras");
    cont.innerHTML = arr.map(e=>{
      if(e.error) return `<div class="emi"><div class="emi-name">${e.emisora}</div><div class="sig">⚠️ ${e.error}</div></div>`;
      const badge = e.puntaje>=1 ? "b-green" : e.puntaje<=-1 ? "b-red" : "b-gray";
      const live = (e.live_precio!==undefined)
        ? `$${e.live_precio} ${fmtCambio(e.live_cambio)}`
        : `$${e.precio}`;
      const señales = (e.senales||[]).map(s=>`<div>• ${s}</div>`).join("");
      const alertas = (e.alertas||[]).map(a=>`<div class="alert">⚡ ${a}</div>`).join("");
      return `<div class="emi">
        <div class="emi-top">
          <div class="emi-name">${e.emisora}
            <span class="badge ${badge}">${e.recomendacion.replace(/[🟢🔴⚪⚡]/g,"").trim()||"—"}</span>
          </div>
          <div class="emi-price">${live}</div>
        </div>
        <div class="sig">RSI ${e.rsi} · sesgo ${e.sesgo} · puntaje ${e.puntaje>=0?"+":""}${e.puntaje}</div>
        <div class="sig">${señales}${alertas}</div>
      </div>`;
    }).join("");
  }catch(e){ console.error(e); }
}

function tick(){
  cd--; document.getElementById("cd").textContent = cd;
  if(cd<=0){ cd = REFRESH; refrescar(); }
}
function refrescar(){ cargarPanorama(); cargarEmisoras();
  document.getElementById("reloj").textContent = new Date().toLocaleTimeString("es-MX"); }

refrescar();
setInterval(tick, 1000);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    print("=" * 60)
    print("  Dashboard del Agente de Inversión")
    print("  Abre en tu navegador:  http://localhost:8000")
    print("  ⚠️  Análisis informativo. No es asesoría financiera.")
    print("=" * 60)
    app.run(host="127.0.0.1", port=8000, debug=False)
