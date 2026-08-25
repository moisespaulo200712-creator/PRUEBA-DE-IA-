"""Configuración central del agente de inversión."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Credenciales (desde .env) ---
DATABURSATIL_TOKEN = os.getenv("DATABURSATIL_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Emisoras a vigilar por defecto (ticker de Yahoo con sufijo .MX) ---
EMISORAS_DEFAULT = [
    "AMXB.MX",      # América Móvil
    "WALMEX.MX",    # Walmart de México
    "GFNORTEO.MX",  # Grupo Financiero Banorte
    "CEMEXCPO.MX",  # Cemex
    "FEMSAUBD.MX",  # FEMSA
]

# --- Umbrales de las señales (ajústalos a tu gusto) ---
RSI_SOBRECOMPRA = 70        # RSI por encima => posible sobrecompra
RSI_SOBREVENTA = 30         # RSI por debajo => posible sobreventa
VOLUMEN_INUSUAL_FACTOR = 2.0  # volumen del día > 2x el promedio => inusual
MOVIMIENTO_FUERTE_PCT = 4.0   # variación diaria > 4% => movimiento fuerte

# --- Noticias: fuentes RSS de medios financieros MX ---
FUENTES_RSS = [
    "https://www.eleconomista.com.mx/rss/mercados.xml",
    "https://www.elfinanciero.com.mx/arc/outboundfeeds/rss/category/mercados/",
]

# Carpeta donde se guardan los reportes
CARPETA_REPORTES = "reportes"
