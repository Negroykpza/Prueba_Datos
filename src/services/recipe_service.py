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
        if not dish_name:
            return None
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
        if not pos_dishes:
            return mapped, unmapped

        for dish in pos_dishes:
            if dish and self.get_recipe(dish) is not None:
                mapped.append(dish)
            elif dish:
                unmapped.append(dish)
        return mapped, unmapped

    def sync_with_detected_dishes(self, detected_dishes: Optional[List[str]]):
        """
        Sincroniza el catálogo de escandallos con los platos detectados en ventas POS.
        Registra e inicializa únicamente aquellos platos que no tengan escandallo definido,
        manejando listas vacías o valores nulos de forma robusta sin sobrescribir recetas existentes.
        """
        if not detected_dishes:
            return

        changes = False
        for dish in detected_dishes:
            if not dish or not str(dish).strip():
                continue

            clean = str(dish).strip().title()

            # Evitar sobrescribir recetas existentes
            if self.get_recipe(clean) is not None:
                continue

            # Deducción gastronómica inteligente de insumo común y precio en $ CLP
            suggested_ing = "Insumo Perecible Principal"
            default_price = float(DEFAULT_INGREDIENT_PRICES_CLP.get("default", 6500.0))
            dose_qty = 180.0
            recipe_unit = "gramos"
            purchase_unit = "kg"
            factor = 0.001

            dish_lower = clean.lower()
            if any(w in dish_lower for w in ["ceviche", "pescado", "reineta"]):
                suggested_ing = "Pescado Blanco Fresco (Reineta)"
                default_price = 9500.0
                dose_qty = 180.0
            elif any(w in dish_lower for w in ["salmón", "salmon"]):
                suggested_ing = "Filete de Salmón Fresco"
                default_price = 14000.0
                dose_qty = 200.0
            elif any(w in dish_lower for w in ["atún", "atun"]):
                suggested_ing = "Atún Fresco"
                default_price = 15000.0
                dose_qty = 180.0
            elif "macha" in dish_lower:
                suggested_ing = "Lenguas de Machas Frescas"
                default_price = 11000.0
                dose_qty = 150.0
            elif any(w in dish_lower for w in ["lomo", "carne", "vacuno", "bife", "filete"]):
                suggested_ing = "Lomo Liso Vacuno"
                default_price = 9800.0
                dose_qty = 220.0
            elif "pollo" in dish_lower:
                suggested_ing = "Pechuga de Pollo"
                default_price = 4800.0
                dose_qty = 200.0
            elif any(w in dish_lower for w in ["empanada", "pino"]):
                suggested_ing = "Carne Picada Vacuno (Posta)"
                default_price = 7500.0
                dose_qty = 120.0
            elif any(w in dish_lower for w in ["pastel", "choclo"]):
                suggested_ing = "Pasta de Choclo"
                default_price = 3800.0
                dose_qty = 250.0
            elif "cazuela" in dish_lower:
                suggested_ing = "Corte de Vacuno (Osobuco/Tapa Pecho)"
                default_price = 6800.0
                dose_qty = 250.0

            new_rec = Recipe(
                dish_name=clean,
                categoria="Carta General",
                ingredients=[
                    IngredientRequirement(
                        ingredient_name=suggested_ing,
                        quantity_per_dish=dose_qty,
                        recipe_unit=recipe_unit,
                        purchase_unit=purchase_unit,
                        conversion_factor=factor,
                        cost_per_unit=default_price
                    )
                ]
            )
            self.recipes[clean] = new_rec
            changes = True

        if changes:
            self.save_to_disk()

    def ensure_dishes_exist(self, detected_dishes: List[str]):
        """Alias para mantener compatibilidad hacia atrás."""
        self.sync_with_detected_dishes(detected_dishes)

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convierte los escandallos a un DataFrame tabular plano para edición interactiva
        en el editor de Streamlit (Pestaña 2).
        """
        rows = []
        for recipe in self.get_all_recipes():
            if not recipe.ingredients:
                rows.append({
                    "Plato": recipe.dish_name,
                    "Insumo Perecible": "Sin insumo asignado",
                    "Cantidad": 0.0,
                    "Unidad": "gramos",
                    "Precio Compra ($ CLP)": 0.0,
                    "Dosis por Plato": 0.0,
                    "Unidad Receta": "gramos",
                    "Unidad Compra": "kg"
                })
            else:
                for ing in recipe.ingredients:
                    # Normalizar unidad para visualización amigable
                    u_display = ing.recipe_unit
                    if u_display in ["g", "gr"]:
                        u_display = "gramos"
                    elif u_display in ["un"]:
                        u_display = "unidades"
                    elif u_display in ["l"]:
                        u_display = "litros"

                    rows.append({
                        "Plato": recipe.dish_name,
                        "Insumo Perecible": ing.ingredient_name,
                        "Cantidad": float(ing.quantity_per_dish),
                        "Unidad": u_display,
                        "Precio Compra ($ CLP)": float(ing.cost_per_unit),
                        "Dosis por Plato": float(ing.quantity_per_dish),
                        "Unidad Receta": ing.recipe_unit,
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
            plato = str(row.get("Plato", "")).strip().title()
            insumo = str(row.get("Insumo Perecible", "")).strip()

            if not plato or not insumo or insumo == "Sin insumo asignado":
                continue

            dosis_val = row.get("Cantidad", row.get("Dosis por Plato", 100.0))
            try:
                dosis = float(dosis_val)
            except (ValueError, TypeError):
                dosis = 100.0

            precio_val = row.get("Precio Compra ($ CLP)", 5000.0)
            try:
                precio_clp = float(precio_val)
            except (ValueError, TypeError):
                precio_clp = 5000.0

            unit_raw = str(row.get("Unidad", row.get("Unidad Receta", "gramos"))).strip().lower()

            # Normalización y factor de conversión culinario a unidad de compra
            if unit_raw in ["gramos", "g", "gr"]:
                runit = "gramos"
                punit = "kg"
                factor = 0.001
            elif unit_raw in ["kg", "kilos", "kilo"]:
                runit = "kg"
                punit = "kg"
                factor = 1.0
            elif unit_raw in ["ml", "mililitros"]:
                runit = "ml"
                punit = "litro"
                factor = 0.001
            elif unit_raw in ["litros", "litro", "l"]:
                runit = "litros"
                punit = "litro"
                factor = 1.0
            elif unit_raw in ["unidades", "unidad", "un"]:
                runit = "unidades"
                punit = "un"
                factor = 1.0
            else:
                runit = unit_raw
                punit = "kg"
                factor = 0.001

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
                cat = existing.categoria if existing else "Carta General"
                new_recipes[plato] = Recipe(dish_name=plato, categoria=cat, ingredients=[])

            new_recipes[plato].ingredients.append(req)

        self.recipes = new_recipes
        self.save_to_disk()
