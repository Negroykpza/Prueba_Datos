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


if __name__ == "__main__":
    unittest.main()
