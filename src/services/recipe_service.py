"""Servicio para la gestión, almacenamiento y persistencia de escandallos (fichas técnicas simples)."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
from src.config import DEFAULT_RECIPES_PATH, ACTIVE_RECIPES_PATH
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

    def to_dataframe(self) -> pd.DataFrame:
        """Convierte los escandallos a un DataFrame tabular plano para presentación en UI."""
        rows = []
        for recipe in self.get_all_recipes():
            if not recipe.ingredients:
                rows.append({
                    "Plato": recipe.dish_name,
                    "Categoría": recipe.categoria,
                    "Insumo Perecible": "Sin insumos asignados",
                    "Dosis por Plato": 0.0,
                    "Unidad Receta": "-",
                    "Unidad Compra": "-"
                })
            else:
                for ing in recipe.ingredients:
                    rows.append({
                        "Plato": recipe.dish_name,
                        "Categoría": recipe.categoria,
                        "Insumo Perecible": ing.ingredient_name,
                        "Dosis por Plato": ing.quantity_per_dish,
                        "Unidad Receta": ing.recipe_unit,
                        "Unidad Compra": ing.purchase_unit
                    })

        return pd.DataFrame(rows)
