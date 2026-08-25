# Agente de Inversión — Mercado Nacional (BMV/BIVA)

Esqueleto de tu **propio agente de análisis de inversiones** para el mercado
mexicano. Vigila emisoras, calcula indicadores técnicos, detecta movimientos
inusuales (detección temprana), revisa noticias y arma un **reporte de
oportunidades** con alertas.

> ⚠️ **Aviso importante**: Esta es una herramienta de **análisis y alertas**,
> **no** es asesoría financiera ni garantía de rendimientos. Todas las
> decisiones de inversión son **bajo tu propio riesgo**. Invierte solo capital
> que puedas permitirte perder y valida siempre las señales antes de operar.

---

## ¿Qué hace?

El agente está formado por varios "sub-agentes" que trabajan juntos:

| Sub-agente | Archivo | Qué hace |
|---|---|---|
| **Técnico** | `agente_inversion/agentes/tecnico.py` | RSI, medias móviles, MACD, Bollinger → señales de compra/venta |
| **Detección temprana** | `agente_inversion/agentes/deteccion.py` | Detecta volumen/precio inusual (posibles movimientos antes de que sean obvios) |
| **Noticias** | `agente_inversion/agentes/noticias.py` | Lee RSS de medios financieros MX y estima sentimiento |
| **Oportunidades** | `agente_inversion/agentes/oportunidades.py` | Combina todo en un puntaje y arma el reporte final |

La capa de **datos** es intercambiable:

- **Yahoo Finance** (`yfinance`) — gratis, sin registro. Emisoras MX con sufijo `.MX` (ej. `AMXB.MX`, `WALMEX.MX`). Ideal para probar ya.
- **DataBursatil** — gratis (200,000 créditos/mes), datos oficiales BMV/BIVA. Requiere API key: https://databursatil.com/

---

## Instalación

```bash
pip install -r requirements.txt
cp .env.example .env   # y edita tus claves si usas DataBursatil / alertas
```

## Uso rápido (con Yahoo, sin registro)

```bash
python main.py --emisoras AMXB.MX,WALMEX.MX,GFNORTEO.MX,CEMEXCPO.MX
```

Para usar DataBursatil (datos oficiales BMV/BIVA):

```bash
# 1) Regístrate en https://databursatil.com/ y pon tu token en .env
# 2) Ejecuta con --fuente databursatil
python main.py --fuente databursatil --emisoras AMXL,WALMEX,GFNORTEO
```

---

## Estructura

```
agente_inversion/
  datos/            # De dónde salen los precios (Yahoo, DataBursatil)
  indicadores.py    # Cálculo de RSI, medias, MACD, etc. (puro pandas)
  agentes/          # Los sub-agentes de análisis
  alertas.py        # Cómo te avisa (consola, archivo, Telegram opcional)
config.py           # Configuración central
main.py             # Punto de entrada (CLI)
```

## Próximos pasos sugeridos

1. Corre el MVP con Yahoo y revisa los reportes.
2. Saca tu API key de DataBursatil para datos reales de la BMV.
3. Conecta un LLM (Claude/OpenAI) en `agentes/noticias.py` para análisis de
   sentimiento más fino (hay un hook preparado).
4. Programa la ejecución diaria (cron / GitHub Actions) para alertas automáticas.
5. Cuando confíes en las señales, evalúa integrar un bróker en modo *paper*.
