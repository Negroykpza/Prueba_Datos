"""Pruebas unitarias para el servicio de compras sugeridas y conversión de insumos."""

import unittest
from datetime import date
import pandas as pd
from src.services.recipe_service import RecipeService
from src.services.procurement import ProcurementService
from src.models.schema import Recipe, IngredientRequirement


class TestProcurementService(unittest.TestCase):

    def setUp(self):
        self.recipe_service = RecipeService()
        # Limpiar y configurar recetas de prueba controladas
        self.recipe_service.recipes = {
            "Ceviche Mixto": Recipe(
                dish_name="Ceviche Mixto",
                categoria="Pescados",
                ingredients=[
                    IngredientRequirement("Pescado Blanco", 180.0, "g", "kg", 0.001),
                    IngredientRequirement("Cebolla Morada", 50.0, "g", "kg", 0.001),
                ]
            ),
            "Ceviche Clásico": Recipe(
                dish_name="Ceviche Clásico",
                categoria="Pescados",
                ingredients=[
                    IngredientRequirement("Pescado Blanco", 200.0, "g", "kg", 0.001),
                    IngredientRequirement("Limón Sutil", 4.0, "un", "un", 1.0),
                ]
            )
        }
        self.procurement = ProcurementService(self.recipe_service)

    def test_shopping_list_with_unit_conversion_and_aggregation(self):
        # Forecast data:
        # Viernes: Ceviche Mixto = 10 base, 11.5 con margen (1.5 buffer)
        # Sábado: Ceviche Clásico = 10 base, 11.5 con margen (1.5 buffer)
        # Lunes (no fin de semana): Ceviche Mixto = 10 base, 11.5 con margen
        forecast_records = [
            {
                "fecha": date(2026, 8, 14), # Viernes
                "dia_semana_nombre": "Viernes",
                "es_fin_de_semana": True,
                "plato": "Ceviche Mixto",
                "demanda_base": 10.0,
                "margen_seguridad_unidades": 1.5,
                "demanda_con_margen": 11.5
            },
            {
                "fecha": date(2026, 8, 15), # Sábado
                "dia_semana_nombre": "Sábado",
                "es_fin_de_semana": True,
                "plato": "Ceviche Clásico",
                "demanda_base": 10.0,
                "margen_seguridad_unidades": 1.5,
                "demanda_con_margen": 11.5
            },
            {
                "fecha": date(2026, 8, 17), # Lunes
                "dia_semana_nombre": "Lunes",
                "es_fin_de_semana": False,
                "plato": "Ceviche Mixto",
                "demanda_base": 10.0,
                "margen_seguridad_unidades": 1.5,
                "demanda_con_margen": 11.5
            }
        ]
        forecast_df = pd.DataFrame(forecast_records)

        # 1. Probar con filtro solo fin de semana
        shopping_wknd = self.procurement.calculate_shopping_list(forecast_df, only_weekend=True)
        self.assertEqual(len(shopping_wknd), 3) # Pescado Blanco, Cebolla Morada, Limón Sutil

        # Pescado Blanco en fin de semana:
        # Ceviche Mixto (11.5 porciones * 180g = 2.07 kg)
        # Ceviche Clásico (11.5 porciones * 200g = 2.30 kg)
        # Total Pescado Blanco = 4.37 kg
        pescado_row = shopping_wknd[shopping_wknd["insumo"] == "Pescado Blanco"].iloc[0]
        self.assertAlmostEqual(pescado_row["total_sugerido"], 4.37, places=2)
        self.assertEqual(pescado_row["unidad"], "kg")

        # Limón Sutil: 11.5 porciones * 4 un = 46.0 un
        limon_row = shopping_wknd[shopping_wknd["insumo"] == "Limón Sutil"].iloc[0]
        self.assertAlmostEqual(limon_row["total_sugerido"], 46.0, places=1)
        self.assertEqual(limon_row["unidad"], "un")

    def test_whatsapp_message_formatting(self):
        df_mock = pd.DataFrame([
            {"insumo": "Reineta", "total_sugerido": 25.5, "unidad": "kg"},
            {"insumo": "Limón Sutil", "total_sugerido": 120.0, "unidad": "un"}
        ])
        msg = self.procurement.format_whatsapp_message(df_mock, "La Mar Chile", "Fin de Semana")
        self.assertIn("LA MAR CHILE", msg)
        self.assertIn("Reineta", msg)
        self.assertIn("25.5 kg", msg)
        self.assertIn("Limón Sutil", msg)
        self.assertIn("120.0 un", msg)
        self.assertIn("15% margen de seguridad", msg)

    def test_pdf_report_generation(self):
        df_mock = pd.DataFrame([
            {"insumo": "Reineta", "consumo_base": 20.0, "margen_seguridad": 3.0, "total_sugerido": 23.0, "unidad": "kg", "riesgo_caducidad": "CRÍTICO"},
            {"insumo": "Limón Sutil", "consumo_base": 100.0, "margen_seguridad": 15.0, "total_sugerido": 115.0, "unidad": "un", "riesgo_caducidad": "BAJO"}
        ])
        pdf_bytes = self.procurement.generate_pdf_report(df_mock, "Restaurante Test", "Fin de Semana", 15)
        self.assertTrue(len(pdf_bytes) > 0)
        # Un PDF válido comienza con %PDF
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
