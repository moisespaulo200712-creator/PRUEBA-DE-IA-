"""Agente de Inversión — Mercado Nacional (BMV/BIVA).

Uso:
    python main.py --emisoras AMXB.MX,WALMEX.MX
    python main.py --fuente databursatil --emisoras AMXL,WALMEX
    python main.py --solo-oportunidades   # solo muestra señales relevantes

⚠️ Herramienta de análisis. NO es asesoría financiera. Úsala bajo tu riesgo.
"""
import argparse
import sys

import config
from agente_inversion.datos import obtener_proveedor
from agente_inversion.agentes import oportunidades
from agente_inversion import alertas


def parse_args():
    p = argparse.ArgumentParser(description="Agente de inversión BMV/BIVA")
    p.add_argument(
        "--fuente", default="yahoo", choices=["yahoo", "databursatil"],
        help="Fuente de datos (default: yahoo, gratis y sin registro)",
    )
    p.add_argument(
        "--emisoras", default="",
        help="Lista separada por comas. Ej: AMXB.MX,WALMEX.MX",
    )
    p.add_argument(
        "--dias", type=int, default=180,
        help="Días de histórico a analizar (default: 180)",
    )
    p.add_argument(
        "--sin-noticias", action="store_true",
        help="No consultar noticias (más rápido)",
    )
    p.add_argument(
        "--solo-oportunidades", action="store_true",
        help="Mostrar solo emisoras con señal o movimiento inusual",
    )
    return p.parse_args()


def main():
    args = parse_args()
    emisoras = (
        [e.strip() for e in args.emisoras.split(",") if e.strip()]
        or config.EMISORAS_DEFAULT
    )

    print("=" * 60)
    print("  AGENTE DE INVERSIÓN — Mercado Nacional (BMV/BIVA)")
    print(f"  Fuente: {args.fuente}  |  Emisoras: {len(emisoras)}")
    print("  ⚠️  Análisis informativo. No es asesoría financiera.")
    print("=" * 60)

    try:
        proveedor = obtener_proveedor(args.fuente)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    reportes = []
    for emisora in emisoras:
        try:
            df = proveedor.historico(emisora, dias=args.dias)
            reporte = oportunidades.evaluar(
                emisora, df, revisar_noticias=not args.sin_noticias
            )
            reportes.append(reporte)
            alertas.notificar(reporte, solo_oportunidades=args.solo_oportunidades)
        except Exception as e:
            print(f"⚠️  {emisora}: no se pudo analizar ({e})")
            print("-" * 60)

    # Ranking final por puntaje
    if reportes:
        reportes.sort(key=lambda r: r["puntaje"], reverse=True)
        print("\n🏆 RANKING DE OPORTUNIDADES:")
        for r in reportes:
            print(f"   {r['puntaje']:+d}  {r['emisora']:<14} {r['recomendacion']}")


if __name__ == "__main__":
    main()
