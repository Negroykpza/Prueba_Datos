"""Pruebas unitarias para RecipeService y sincronización dinámica de platos."""

import unittest
import tempfile
import json
from pathlib import Path
import pandas as pd
from src.services.recipe_service import RecipeService


class TestRecipeService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name) / "recipes.json"
        self.defaults_path = Path(self.temp_dir.name) / "defaults.json"

        # Crear defaults iniciales
        initial_data = [
            {
                "dish_name": "Ceviche Mixto",
                "categoria": "Pescados y Mariscos",
                "ingredients": [
                    {
                        "ingredient_name": "Pescado Blanco Fresco (Reineta)",
                        "quantity_per_dish": 180.0,
                        "recipe_unit": "gramos",
                        "purchase_unit": "kg",
                        "conversion_factor": 0.001,
                        "cost_per_unit": 9500.0
                    }
                ]
            }
        ]
        with open(self.defaults_path, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        self.service = RecipeService(
            storage_path=self.storage_path,
            defaults_path=self.defaults_path
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sync_with_detected_dishes_new_dish(self):
        # Sincronizar un plato nuevo
        self.service.sync_with_detected_dishes(["Lomo Saltado"])
        recipe = self.service.get_recipe("Lomo Saltado")
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe.dish_name, "Lomo Saltado")
        self.assertTrue(len(recipe.ingredients) > 0)
        self.assertEqual(recipe.ingredients[0].ingredient_name, "Lomo Liso Vacuno")

    def test_sync_with_detected_dishes_does_not_overwrite_existing(self):
        # Modificar receta existente
        recipe = self.service.get_recipe("Ceviche Mixto")
        recipe.ingredients[0].cost_per_unit = 12345.0
        self.service.upsert_recipe(recipe)

        # Sincronizar incluyendo el plato existente
        self.service.sync_with_detected_dishes(["Ceviche Mixto", "Pastel de Choclo"])

        # Verificar que el existente NO fue sobrescrito
        reloaded = self.service.get_recipe("Ceviche Mixto")
        self.assertEqual(reloaded.ingredients[0].cost_per_unit, 12345.0)

        # Verificar que el nuevo plato sí se agregó
        self.assertIsNotNone(self.service.get_recipe("Pastel de Choclo"))

    def test_sync_with_detected_dishes_handles_empty_and_nulls(self):
        # No debe lanzar excepciones con listas vacías o elementos inválidos
        self.service.sync_with_detected_dishes([])
        self.service.sync_with_detected_dishes(None)
        self.service.sync_with_detected_dishes(["", None, "   "])
        self.assertEqual(len(self.service.get_all_recipes()), 1)

    def test_to_dataframe_and_update(self):
        df = self.service.to_dataframe()
        self.assertIn("Plato", df.columns)
        self.assertIn("Insumo Perecible", df.columns)
        self.assertIn("Cantidad", df.columns)
        self.assertIn("Unidad", df.columns)
        self.assertIn("Precio Compra ($ CLP)", df.columns)

        # Modificar y actualizar
        df.loc[df["Plato"] == "Ceviche Mixto", "Cantidad"] = 250.0
        self.service.update_from_dataframe(df)

        reloaded = self.service.get_recipe("Ceviche Mixto")
        self.assertEqual(reloaded.ingredients[0].quantity_per_dish, 250.0)

    def test_get_recipe_cost(self):
        # 180 gramos * 0.001 * 9500 = 1710.0 CLP
        cost = self.service.get_recipe_cost("Ceviche Mixto")
        self.assertEqual(cost, 1710.0)

        # Plato inexistente o vacío
        self.assertEqual(self.service.get_recipe_cost("Plato Fantasma"), 0.0)
        self.assertEqual(self.service.get_recipe_cost(""), 0.0)
        self.assertEqual(self.service.get_recipe_cost(None), 0.0)

    def test_get_menu_engineering_df(self):
        # Caso vacío o None
        empty_df = self.service.get_menu_engineering_df(None)
        self.assertTrue(empty_df.empty)
        self.assertIn("Plato", empty_df.columns)
        self.assertIn("Categoria_Cuadrante", empty_df.columns)

        # Crear datos de ventas simulados con varios platos
        self.service.sync_with_detected_dishes(["Lomo Saltado", "Pastel de Choclo", "Empanada de Pino"])
        sales_data = pd.DataFrame([
            {"fecha": "2026-06-01", "plato": "Ceviche Mixto", "cantidad": 50},
            {"fecha": "2026-06-02", "plato": "Ceviche Mixto", "cantidad": 50},
            {"fecha": "2026-06-01", "plato": "Lomo Saltado", "cantidad": 80},
            {"fecha": "2026-06-01", "plato": "Pastel de Choclo", "cantidad": 10},
            {"fecha": "2026-06-01", "plato": "Empanada de Pino", "cantidad": 20},
        ])

        menu_df = self.service.get_menu_engineering_df(sales_data)
        self.assertFalse(menu_df.empty)
        self.assertEqual(len(menu_df), 4)

        # Verificar columnas obligatorias
        expected_cols = [
            "Plato", "Categoria_Cuadrante", "Precio_Venta", "Costo_Receta",
            "Margen_Unitario", "Margen_Pct", "Unidades_Vendidas", "Margen_Total",
            "Ventas_Totales", "Costo_Total_Insumos", "Mix_Ventas_Pct"
        ]
        for col in expected_cols:
            self.assertIn(col, menu_df.columns)

        # Verificar que Lomo Saltado tiene 80 unidades y Ceviche Mixto tiene 100 unidades
        ceviche_row = menu_df[menu_df["Plato"] == "Ceviche Mixto"].iloc[0]
        self.assertEqual(ceviche_row["Unidades_Vendidas"], 100.0)
        self.assertEqual(ceviche_row["Costo_Receta"], 1710.0)
        self.assertTrue(ceviche_row["Precio_Venta"] > ceviche_row["Costo_Receta"])
        self.assertTrue(ceviche_row["Margen_Unitario"] > 0)
        self.assertTrue(ceviche_row["Margen_Total"] > 0)
        self.assertEqual(ceviche_row["Ventas_Totales"], ceviche_row["Unidades_Vendidas"] * ceviche_row["Precio_Venta"])
        self.assertEqual(ceviche_row["Costo_Total_Insumos"], ceviche_row["Unidades_Vendidas"] * ceviche_row["Costo_Receta"])

        # Verificar que todos los platos tienen una categoría cuadrante válida
        valid_quadrants = {
            "🌟 Estrella",
            "🐎 Caballo de Batalla",
            "🧩 Rompecabezas",
            "🐕 Perro"
        }
        for cat in menu_df["Categoria_Cuadrante"]:
            self.assertIn(cat, valid_quadrants)

        # Verificar orden descendente por Margen Total
        margenes = menu_df["Margen_Total"].tolist()
        self.assertEqual(margenes, sorted(margenes, reverse=True))

        # Verificar que la suma de Mix_Ventas_Pct sea cercana a 100%
        mix_sum = menu_df["Mix_Ventas_Pct"].sum()
        self.assertAlmostEqual(mix_sum, 100.0, places=0)

    def test_update_from_dataframe_with_filtered_dish(self):
        # Sincronizar dos platos
        self.service.sync_with_detected_dishes(["Lomo Saltado", "Pastel de Choclo"])
        all_dishes_before = set(self.service.recipes.keys())
        self.assertEqual(len(all_dishes_before), 3)
        self.assertIsNotNone(self.service.get_recipe("Ceviche Mixto"))
        self.assertIsNotNone(self.service.get_recipe("Lomo Saltado"))
        self.assertIsNotNone(self.service.get_recipe("Pastel de Choclo"))

        # Obtener dataframe completo y filtrar solo Ceviche Mixto
        df_full = self.service.to_dataframe()
        ceviche_df = df_full[df_full["Plato"] == "Ceviche Mixto"].copy()
        ceviche_df["Cantidad"] = 350.0

        # Guardar únicamente el plato filtrado
        self.service.update_from_dataframe(ceviche_df, filtered_dish="Ceviche Mixto")

        # Verificar que Ceviche Mixto fue actualizado
        ceviche_recipe = self.service.get_recipe("Ceviche Mixto")
        self.assertEqual(ceviche_recipe.ingredients[0].quantity_per_dish, 350.0)

        # Verificar que los otros platos NO fueron eliminados ni modificados
        all_dishes_after = set(self.service.recipes.keys())
        self.assertEqual(all_dishes_before, all_dishes_after)
        self.assertIsNotNone(self.service.get_recipe("Lomo Saltado"))
        self.assertIsNotNone(self.service.get_recipe("Pastel de Choclo"))


if __name__ == "__main__":
    unittest.main()

