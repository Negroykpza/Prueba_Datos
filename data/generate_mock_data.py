"""Script generador de datos sintéticos realistas de ventas POS para restaurantes en Chile.

Genera un historial de ventas de los últimos 90 días respetando la dinámica gastronómica chilena:
- Días lunes y martes: volumen base de consumo.
- Días viernes y sábado: el doble de ventas (2x) respecto a lunes y martes.
- Domingo: alta concentración en almuerzo familiar.
- Platos típicos de la cocina chilena y restobares (ceviches, lomo saltado, pastel de choclo, etc.).
"""

import sys
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

# Configurar stdout para evitar errores de codificación en Windows CP1252
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def generate_sales_data(days: int = 90, end_date: date = None) -> pd.DataFrame:
    if end_date is None:
        end_date = date.today()

    start_date = end_date - timedelta(days=days - 1)

    # Catálogo de platos típicos de restaurante chileno con su volumen base de venta diaria (Lunes/Martes)
    dishes_config = {
        "Ceviche Mixto": {"base_qty": 14, "std_dev": 2.5},
        "Ceviche Clásico": {"base_qty": 16, "std_dev": 3.0},
        "Lomo Saltado": {"base_qty": 15, "std_dev": 2.8},
        "Pastel de Choclo": {"base_qty": 11, "std_dev": 2.0},
        "Salmón Grillé": {"base_qty": 10, "std_dev": 2.0},
        "Tartar de Atún": {"base_qty": 8, "std_dev": 1.8},
        "Empanada de Pino": {"base_qty": 22, "std_dev": 4.0},
        "Machas a la Parmesana": {"base_qty": 12, "std_dev": 2.2},
        "Cazuela de Vacuno": {"base_qty": 9, "std_dev": 1.5}
    }

    # Factores multiplicadores por día de la semana (0: Lunes, 6: Domingo)
    # Lunes y Martes = 1.0 (base)
    # Viernes y Sábado = 2.0+ (el doble de ventas que lunes y martes)
    weekday_multipliers = {
        0: 1.00,  # Lunes (base)
        1: 1.00,  # Martes (base)
        2: 1.15,  # Miércoles
        3: 1.35,  # Jueves (after-office / previa)
        4: 2.05,  # Viernes (peak fin de semana: >2x de lunes/martes)
        5: 2.25,  # Sábado (peak máximo: >2x de lunes/martes)
        6: 1.65   # Domingo (almuerzos familiares)
    }

    records = []
    np.random.seed(42)  # Semilla para reproducibilidad de pruebas

    current_date = start_date
    while current_date <= end_date:
        dow = current_date.weekday()
        multiplier = weekday_multipliers[dow]

        for dish, config in dishes_config.items():
            base = config["base_qty"]
            std = config["std_dev"]

            # Media esperada escalada por el día de la semana
            expected_mean = base * multiplier
            
            # Variación aleatoria realista con distribución normal
            simulated_qty = int(np.round(np.random.normal(expected_mean, std)))

            # Asegurar un mínimo operacional positivo
            simulated_qty = max(1, simulated_qty)

            records.append({
                "Fecha": current_date.strftime("%d/%m/%Y"),
                "Plato": dish,
                "Cantidad Vendida": simulated_qty
            })

        current_date += timedelta(days=1)

    df = pd.DataFrame(records)
    return df


def main():
    output_dir = Path(__file__).resolve().parent
    sample_file_path = output_dir / "sample_pos_sales.csv"
    history_file_path = output_dir / "ventas_pos_90dias.csv"

    print("[INFO] Generando dataset de ventas sintéticas para restaurante en Chile (90 días)...")
    df = generate_sales_data(days=90)

    # Guardar en ambos destinos (para la demo del SaaS y respaldo de 90 días)
    df.to_csv(sample_file_path, index=False, encoding="utf-8")
    df.to_csv(history_file_path, index=False, encoding="utf-8")

    print(f"[OK] Archivo generado exitosamente en: {sample_file_path}")
    print(f"[OK] Archivo generado exitosamente en: {history_file_path}")

    # Análisis de validación de los patrones semanales
    temp_df = df.copy()
    temp_df["dt"] = pd.to_datetime(temp_df["Fecha"], format="%d/%m/%Y")
    temp_df["dia_semana"] = temp_df["dt"].dt.day_name()
    temp_df["dow"] = temp_df["dt"].dt.dayofweek

    promedios = (
        temp_df.groupby(["dow", "dia_semana"])["Cantidad Vendida"]
        .mean()
        .reset_index()
        .sort_values(by="dow")
    )

    print("\n[VALIDACIÓN] Ventas Promedio por Plato según Día de la Semana:")
    nombres_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    for _, row in promedios.iterrows():
        dow_idx = int(row["dow"])
        prom = row["Cantidad Vendida"]
        print(f"  - {nombres_es[dow_idx]:<10}: {prom:.1f} unidades por plato")

    lunes_martes_avg = promedios[promedios["dow"].isin([0, 1])]["Cantidad Vendida"].mean()
    viernes_sabado_avg = promedios[promedios["dow"].isin([4, 5])]["Cantidad Vendida"].mean()
    ratio = viernes_sabado_avg / lunes_martes_avg if lunes_martes_avg > 0 else 0

    print(f"\n[METRICA] Ratio Viernes-Sábado vs Lunes-Martes: {ratio:.2f}x (Objetivo: ~2.0x)")
    print(f"[METRICA] Total de filas generadas: {len(df)} registros ({df['Plato'].nunique()} platos en 90 días)\n")


if __name__ == "__main__":
    main()
