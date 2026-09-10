"""Pruebas unitarias para el motor de predicción (promedio día de semana + 15% de margen)."""

import unittest
from datetime import date
import pandas as pd
from src.services.forecasting import ForecastingEngine


class TestForecastingEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ForecastingEngine(safety_margin=0.15)
        # Construir dataset controlado: 2 sábados y 2 domingos
        # Sábado 1: 01/08/2026 -> 20 unidades
        # Sábado 2: 08/08/2026 -> 40 unidades -> Promedio Sábado = 30 unidades
        # Domingo 1: 02/08/2026 -> 10 unidades
        # Domingo 2: 09/08/2026 -> 10 unidades -> Promedio Domingo = 10 unidades
        data = [
            {"fecha": date(2026, 8, 1), "plato": "Ceviche Mixto", "cantidad": 20.0},
            {"fecha": date(2026, 8, 2), "plato": "Ceviche Mixto", "cantidad": 10.0},
            {"fecha": date(2026, 8, 8), "plato": "Ceviche Mixto", "cantidad": 40.0},
            {"fecha": date(2026, 8, 9), "plato": "Ceviche Mixto", "cantidad": 10.0},
        ]
        self.sales_df = pd.DataFrame(data)

    def test_day_of_week_averages(self):
        profiles = self.engine.calculate_day_of_week_profiles(self.sales_df)
        sat_profile = profiles[profiles["dia_semana_num"] == 5].iloc[0]
        sun_profile = profiles[profiles["dia_semana_num"] == 6].iloc[0]

        # Promedio Sábado: (20 + 40) / 2 = 30.0
        self.assertEqual(sat_profile["promedio_diario"], 30.0)
        # Promedio Domingo: (10 + 10) / 2 = 10.0
        self.assertEqual(sun_profile["promedio_diario"], 10.0)

    def test_safety_margin_calculation(self):
        # Proyectar empezando en un Sábado (15/08/2026 es Sábado)
        start_sat = date(2026, 8, 15)
        proj = self.engine.project_next_days(
            self.sales_df,
            start_date=start_sat,
            days_horizon=7,
            safety_margin=0.15
        )

        self.assertEqual(len(proj), 7)

        # El primer día proyectado es sábado
        first_day = proj.iloc[0]
        self.assertEqual(first_day["dia_semana_num"], 5)
        self.assertEqual(first_day["demanda_base"], 30.0)
        # Margen 15%: 30 * 0.15 = 4.5
        self.assertEqual(first_day["margen_seguridad_unidades"], 4.5)
        # Demanda con margen: 30 + 4.5 = 34.5
        self.assertEqual(first_day["demanda_con_margen"], 34.5)
        self.assertTrue(first_day["es_fin_de_semana"])


if __name__ == "__main__":
    unittest.main()
