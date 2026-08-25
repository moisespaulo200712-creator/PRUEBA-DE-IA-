# 📈 Guía completa — Tu Agente de Inversión (BMV/BIVA)

Todo lo que necesitas para correr tu agente **en tu Mac** y empezar a ver
oportunidades de inversión en el mercado mexicano.

> ⚠️ **Aviso**: Esta es una herramienta de **análisis y alertas**. **NO es
> asesoría financiera** ni garantía de ganancias. Todas las decisiones son
> **bajo tu propio riesgo**. Invierte solo lo que puedas permitirte perder.

---

## 🧭 ¿Qué es esto?

Un "robot" (agente) que vigila acciones de la Bolsa Mexicana y te dice dónde
hay posibles oportunidades. Está formado por varios sub-agentes:

- **Técnico** → calcula RSI, medias móviles, MACD, Bollinger (señales de compra/venta)
- **Detección temprana** → caza movimientos inusuales (volumen o precio raros) antes de que sean obvios
- **Noticias** → lee titulares financieros y estima si el ánimo es positivo o negativo
- **Oportunidades** → junta todo en un puntaje y un ranking
- **Analista IA (Claude)** → interpreta todo en lenguaje natural y prioriza ideas

---

## 💻 PARTE 1 — Instalarlo en tu Mac (paso a paso)

> En Mac los comandos son **`python3`** y **`pip3`** (no `python`/`pip`).
> Las líneas que empiezan con `#` son notas — **no las pegues** en la terminal.
> Pega **un bloque a la vez**.

### Paso 1 — ¿Tienes Python?

```bash
python3 --version
```

- Si responde `Python 3.x.x` → listo, sigue al Paso 2.
- Si aparece una ventana ofreciendo instalar *Command Line Tools* → dale
  **Instalar** y espera. Eso instala `python3` y `git`.

### Paso 2 — Descargar el proyecto

```bash
cd ~/Desktop
git clone https://github.com/moisespaulo200712-creator/PRUEBA-DE-IA-.git
cd PRUEBA-DE-IA-
git checkout claude/investment-agents-national-markets-7ws7v5
```

Esto baja el agente a tu **Escritorio** y entra a la carpeta.

### Paso 3 — Instalar las librerías

```bash
python3 -m pip install -r requirements.txt
```

### Paso 4 — (Opcional) Conectar Claude

Para que Claude te dé el análisis en lenguaje natural:

1. Saca tu API key en https://console.anthropic.com/ (sección *API Keys*).
2. Crea tu archivo de configuración y ábrelo:

```bash
cp .env.example .env
open -e .env
```

3. En la línea `ANTHROPIC_API_KEY=` pega tu clave (queda
   `ANTHROPIC_API_KEY=sk-ant-...`), guarda con **Cmd+S** y cierra.

> Nota: la API de Claude tiene costo por uso (muy bajo para este uso, unos
> centavos por análisis). Si no quieres usarla todavía, salta este paso y
> corre el agente **sin** `--ia`.

---

## ▶️ PARTE 2 — Cómo usarlo

### Uso básico (gratis, sin Claude)

```bash
python3 main.py --emisoras AMXB.MX,WALMEX.MX,GFNORTEO.MX,GMEXICOB.MX
```

Te muestra señales, detección temprana y un **ranking de oportunidades**.

### Con análisis de Claude

```bash
python3 main.py --emisoras AMXB.MX,WALMEX.MX,GFNORTEO.MX,GMEXICOB.MX --ia
```

### Solo lo relevante (filtra ruido)

```bash
python3 main.py --emisoras AMXB.MX,WALMEX.MX,GFNORTEO.MX --solo-oportunidades
```

### Opciones disponibles

| Bandera | Qué hace |
|---|---|
| `--emisoras` | Lista separada por comas (ej. `AMXB.MX,WALMEX.MX`) |
| `--fuente` | `yahoo` (gratis) o `databursatil` (oficial BMV/BIVA) |
| `--dias` | Días de histórico a analizar (default 180) |
| `--ia` | Activa el análisis de Claude |
| `--sin-noticias` | Más rápido, sin leer noticias |
| `--solo-oportunidades` | Solo muestra emisoras con señal clara |

### Tickers útiles de la BMV (para Yahoo, con sufijo `.MX`)

| Empresa | Ticker |
|---|---|
| América Móvil | `AMXB.MX` |
| Walmart de México | `WALMEX.MX` |
| Banorte | `GFNORTEO.MX` |
| Grupo México | `GMEXICOB.MX` |
| FEMSA | `FEMSAUBD.MX` |
| Cemex | `CEMEXCPO.MX` |
| Bimbo | `BIMBOA.MX` |
| Kimberly-Clark México | `KIMBERA.MX` |

> Para datos **oficiales** de la BMV/BIVA usa DataBursatil (gratis, 200k
> créditos/mes): regístrate en https://databursatil.com/, pon tu token en
> `.env` y corre con `--fuente databursatil` (las claves ahí van **sin**
> el `.MX`, ej. `AMXL`, `WALMEX`).

---

## 💡 PARTE 3 — Opciones de inversión (panorama actual)

**Contexto del mercado:** El IPC ronda los **65,000 puntos**; 2025 cerró
**+29.9%** y para 2026 los analistas esperan rendimiento de doble dígito.
Motores: **tasas a la baja** y **nearshoring**.

### 3 ideas según tu tolerancia al riesgo

🟢 **Conservador → WALMEX (Walmart de México)**
La gente siempre compra despensa. Operación estable, dividendos, crecimiento
parejo. La opción "para dormir tranquilo".

🟡 **Moderado → GMÉXICO (GMEXICOB / Grupo México)**
La estrella del **nearshoring** por Ferromex (ferrocarril que mueve carga a
EE.UU.). Flujo de caja récord. En el radar de GBM y Actinver.

🟡 **Apuesta a tasas a la baja → GFNORTE (Banorte)**
Cuando bajan las tasas, la banca coloca más crédito y gana. Si crees que
Banxico seguirá bajando, se beneficia.

### Cómo decidir cuál te conviene

Pregúntate:
1. **¿Cuánto puedo invertir?** (empieza pequeño para aprender)
2. **¿Aguanto ver que baje y se recupere, o me estresa?**
3. **¿Puedo dejar el dinero quieto meses/años, o lo necesito pronto?**

- Miedo a la volatilidad + largo plazo → **WALMEX**
- Aguantas vaivenes + crees en el nearshoring → **GMÉXICO**
- Apuestas a la macro (tasas) → **GFNORTE**

> 💡 **Regla de oro para empezar:** diversifica (no metas todo en una sola),
> invierte poco al principio, y no inviertas dinero que puedas necesitar pronto.

---

## 🚀 PARTE 4 — Próximos pasos

1. **Corre el agente** con las emisoras que te interesen y revisa el ranking.
2. **Abre una cuenta** en una casa de bolsa (GBM, Kuspit, Hey Banco, etc.)
   para poder comprar de verdad cuando decidas.
3. **Automatiza**: podemos programar que corra cada mañana y te avise por
   Telegram (con GitHub Actions).
4. **Backtesting**: probar qué tan buenas han sido las señales en el pasado
   antes de confiar en ellas con dinero real.

---

## ❓ ¿Problemas al instalar?

- `command not found: python` → usa **`python3`** (con el 3).
- `command not found: pip` → usa **`python3 -m pip`**.
- `command not found: #` → esa línea es un comentario, **no la pegues**.
- Error al bajar precios → revisa que el ticker lleve `.MX` y tengas internet.

Cualquier error, cópialo y pégamelo aquí y te ayudo. 💬

---

*Herramienta informativa. No constituye asesoría financiera. Invierte bajo tu
propio riesgo.*
