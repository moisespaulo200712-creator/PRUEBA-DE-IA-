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
from agente_inversion.agentes import oportunidades, analista_ia, mercado, fundamental
from agente_inversion import alertas, backtest


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
    p.add_argument(
        "--ia", action="store_true",
        help="Pedir a Claude un análisis global (requiere ANTHROPIC_API_KEY)",
    )
    p.add_argument(
        "--backtest", action="store_true",
        help="Medir qué tan seguido acertaron las señales en el pasado",
    )
    p.add_argument(
        "--horizonte", type=int, default=10,
        help="Backtest: días hacia adelante para medir el rendimiento (default: 10)",
    )
    p.add_argument(
        "--sin-panorama", action="store_true",
        help="No mostrar el panorama de mercado (alzas/bajas y noticias)",
    )
    p.add_argument(
        "--fundamental", action="store_true",
        help="Mostrar análisis fundamental (ingresos, utilidad, deuda, crecimiento)",
    )
    return p.parse_args()


def correr_backtest(proveedor, emisoras, args):
    """Modo backtest: evalúa históricamente las señales de cada emisora."""
    # El backtest necesita bastante historia; pedimos al menos ~1.5 años.
    dias = max(args.dias, 400)
    for emisora in emisoras:
        try:
            df = proveedor.historico(emisora, dias=dias)
            resultado = backtest.correr(emisora, df, horizonte=args.horizonte)
            print(backtest.formatear(resultado))
            print("-" * 60)
        except Exception as e:
            print(f"⚠️  {emisora}: no se pudo hacer backtest ({e})")
            print("-" * 60)


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

    if args.backtest:
        print("\n🔬 MODO BACKTEST — probando las señales contra el pasado\n")
        correr_backtest(proveedor, emisoras, args)
        return

    # Panorama de mercado (si hay token de DataBursatil).
    if not args.sin_panorama:
        try:
            pan = mercado.panorama()
            if pan:
                print(mercado.formatear(pan))
                print("=" * 60)
        except Exception as e:
            print(f"(No se pudo cargar el panorama de mercado: {e})")

    reportes = []
    for emisora in emisoras:
        try:
            df = proveedor.historico(emisora, dias=args.dias)
            reporte = oportunidades.evaluar(
                emisora, df, revisar_noticias=not args.sin_noticias
            )
            reportes.append(reporte)
            alertas.notificar(reporte, solo_oportunidades=args.solo_oportunidades)
            if args.fundamental:
                try:
                    print(fundamental.formatear(fundamental.analizar(emisora)))
                    print("-" * 60)
                except Exception as e:
                    print(f"   (fundamental no disponible: {e})")
        except Exception as e:
            print(f"⚠️  {emisora}: no se pudo analizar ({e})")
            print("-" * 60)

    # Ranking final por puntaje
    if reportes:
        reportes.sort(key=lambda r: r["puntaje"], reverse=True)
        print("\n🏆 RANKING DE OPORTUNIDADES:")
        for r in reportes:
            print(f"   {r['puntaje']:+d}  {r['emisora']:<14} {r['recomendacion']}")

        # Análisis con Claude (opcional)
        if args.ia:
            print("\n🤖 ANÁLISIS DE CLAUDE:")
            print("=" * 60)
            print(analista_ia.analizar(reportes))
            print("=" * 60)


if __name__ == "__main__":
    main()
