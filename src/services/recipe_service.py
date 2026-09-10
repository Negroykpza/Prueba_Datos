"""Servicio para la gestión, almacenamiento y persistencia de escandallos con costeo en pesos chilenos ($ CLP)."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
from src.config import DEFAULT_RECIPES_PATH, ACTIVE_RECIPES_PATH, DEFAULT_INGREDIENT_PRICES_CLP
from src.models.schema import Recipe, IngredientRequirement


class RecipeService:
    """Administra los escandallos e insumos perecibles asociados a cada plato de la carta."""

    def __init__(self, storage_path: Optional[Path] = None, defaults_path: Optional[Path] = None):
        self.storage_path = storage_path or ACTIVE_RECIPES_PATH
        self.defaults_path = defaults_path or DEFAULT_RECIPES_PATH
        self.recipes: Dict[str, Recipe] = {}
        self._initialize_storage()

    def _initialize_storage(self):
        """Inicializa el archivo de escandallos a partir de los valores por defecto si no existe."""
        if not self.storage_path.exists():
            if self.defaults_path.exists():
                with open(self.defaults_path, "r", encoding="utf-8") as f:
                    default_data = json.load(f)
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.storage_path, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, indent=2, ensure_ascii=False)
            else:
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.storage_path, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=2, ensure_ascii=False)

        self.load_recipes()

    def load_recipes(self) -> Dict[str, Recipe]:
        """Carga los escandallos desde el archivo de almacenamiento JSON."""
        if not self.storage_path.exists():
            self._initialize_storage()

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.recipes = {item["dish_name"]: Recipe.from_dict(item) for item in data}
        except Exception:
            self.recipes = {}

        return self.recipes

    def save_to_disk(self):
        """Persiste la lista actual de escandallos en disco."""
        data = [recipe.to_dict() for recipe in self.recipes.values()]
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_all_recipes(self) -> List[Recipe]:
        """Retorna todos los escandallos registrados ordenados alfabéticamente."""
        return sorted(list(self.recipes.values()), key=lambda r: r.dish_name)

    def get_recipe(self, dish_name: str) -> Optional[Recipe]:
        """Busca un escandallo por nombre de plato (búsqueda insensible a mayúsculas/minúsculas)."""
        clean_name = dish_name.strip().lower()
        for name, recipe in self.recipes.items():
            if name.strip().lower() == clean_name:
                return recipe
        return None

    def upsert_recipe(self, recipe: Recipe):
        """Crea o actualiza un escandallo y guarda los cambios en disco."""
        self.recipes[recipe.dish_name] = recipe
        self.save_to_disk()

    def delete_recipe(self, dish_name: str) -> bool:
        """Elimina un escandallo si existe."""
        if dish_name in self.recipes:
            del self.recipes[dish_name]
            self.save_to_disk()
            return True
        return False

    def reset_to_defaults(self):
        """Restablece los escandallos a las recetas iniciales predeterminadas."""
        if self.defaults_path.exists():
            with open(self.defaults_path, "r", encoding="utf-8") as f:
                default_data = json.load(f)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)
            self.load_recipes()

    def get_coverage(self, pos_dishes: List[str]) -> Tuple[List[str], List[str]]:
        """Compara los platos que se venden en el POS con los escandallos configurados."""
        mapped = []
        unmapped = []
        for dish in pos_dishes:
            if self.get_recipe(dish) is not None:
                mapped.append(dish)
            else:
                unmapped.append(dish)
        return mapped, unmapped

    def ensure_dishes_exist(self, detected_dishes: List[str]):
        """
        Asegura que todos los platos detectados dinámicamente en el CSV tengan
        al menos una receta base para que aparezcan en el editor interactivo.
        """
        changes = False
        for dish in detected_dishes:
            clean = dish.strip().title()
            if not self.get_recipe(clean):
                # Generar insumo sugerido con precio base
                suggested_ing = "Insumo Perecible Principal"
                default_price = float(DEFAULT_INGREDIENT_PRICES_CLP["default"])
                
                # Deducción inteligente de insumo común
                dish_lower = clean.lower()
                if "ceviche" in dish_lower or "pescado" in dish_lower or "reineta" in dish_lower:
                    suggested_ing = "Pescado Blanco Fresco (Reineta)"
                    default_price = 9500.0
                elif "salmón" in dish_lower or "salmon" in dish_lower:
                    suggested_ing = "Filete de Salmón Fresco"
                    default_price = 14000.0
                elif "lomo" in dish_lower or "carne" in dish_lower or "vacuno" in dish_lower:
                    suggested_ing = "Lomo Liso Vacuno"
                    default_price = 9800.0
                elif "pollo" in dish_lower:
                    suggested_ing = "Pechuga de Pollo"
                    default_price = 4800.0

                new_rec = Recipe(
                    dish_name=clean,
                    categoria="Carta General",
                    ingredients=[
                        IngredientRequirement(
                            ingredient_name=suggested_ing,
                            quantity_per_dish=180.0,
                            recipe_unit="g",
                            purchase_unit="kg",
                            conversion_factor=0.001,
                            cost_per_unit=default_price
                        )
                    ]
                )
                self.recipes[clean] = new_rec
                changes = True

        if changes:
            self.save_to_disk()

    def to_dataframe(self) -> pd.DataFrame:
        """Convierte los escandallos a un DataFrame tabular plano para edición interactiva en Streamlit."""
        rows = []
        for recipe in self.get_all_recipes():
            if not recipe.ingredients:
                rows.append({
                    "Plato": recipe.dish_name,
                    "Insumo Perecible": "Sin insumo asignado",
                    "Dosis por Plato": 0.0,
                    "Unidad Receta": "g",
                    "Precio Compra ($ CLP)": 0.0,
                    "Unidad Compra": "kg"
                })
            else:
                for ing in recipe.ingredients:
                    rows.append({
                        "Plato": recipe.dish_name,
                        "Insumo Perecible": ing.ingredient_name,
                        "Dosis por Plato": float(ing.quantity_per_dish),
                        "Unidad Receta": ing.recipe_unit,
                        "Precio Compra ($ CLP)": float(ing.cost_per_unit),
                        "Unidad Compra": ing.purchase_unit
                    })

        return pd.DataFrame(rows)

    def update_from_dataframe(self, df: pd.DataFrame):
        """
        Reconstruye y persiste la lista de escandallos a partir de los datos editados
        en el st.data_editor de Streamlit.
        """
        if df.empty:
            return

        new_recipes: Dict[str, Recipe] = {}

        for _, row in df.iterrows():
            plato = str(row["Plato"]).strip().title()
            insumo = str(row["Insumo Perecible"]).strip()
            
            if not plato or not insumo or insumo == "Sin insumo asignado":
                continue

            try:
                dosis = float(row["Dosis por Plato"])
            except (ValueError, TypeError):
                dosis = 100.0

            try:
                precio_clp = float(row["Precio Compra ($ CLP)"])
            except (ValueError, TypeError):
                precio_clp = 5000.0

            runit = str(row.get("Unidad Receta", "g")).strip().lower()
            punit = str(row.get("Unidad Compra", "kg")).strip().lower()

            factor = 0.001 if (runit == "g" and punit == "kg") or (runit == "ml" and punit == "l") else 1.0

            req = IngredientRequirement(
                ingredient_name=insumo,
                quantity_per_dish=dosis,
                recipe_unit=runit,
                purchase_unit=punit,
                conversion_factor=factor,
                cost_per_unit=precio_clp
            )

            if plato not in new_recipes:
                existing = self.get_recipe(plato)
                cat = existing.categoria if existing else "General"
                new_recipes[plato] = Recipe(dish_name=plato, categoria=cat, ingredients=[])

            new_recipes[plato].ingredients.append(req)

        self.recipes = new_recipes
        self.save_to_disk()
