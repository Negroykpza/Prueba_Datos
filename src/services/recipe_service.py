"""Servicio para la gestión, almacenamiento y persistencia de escandallos con costeo en pesos chilenos ($ CLP)."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
from src.config import (
    DEFAULT_RECIPES_PATH,
    ACTIVE_RECIPES_PATH,
    DEFAULT_INGREDIENT_PRICES_CLP,
    DEFAULT_DISH_SALE_PRICES_CLP
)
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
        """Busca un escandallo por nombre de plato (insensible a mayúsculas, espacios y tildes)."""
        if not dish_name:
            return None
        clean_name = str(dish_name).strip().lower()
        for name, recipe in self.recipes.items():
            if name.strip().lower() == clean_name:
                return recipe

        # Fallback normalizado sin tildes/diacríticos
        import unicodedata
        def _strip(s: str) -> str:
            return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

        target_norm = _strip(clean_name)
        for name, recipe in self.recipes.items():
            if _strip(name.strip().lower()) == target_norm:
                return recipe

        return None

    def get_recipe_cost(self, dish_name: str) -> float:
        """
        Calcula el costo total de insumos de una receta en $ CLP.
        Suma (ing.quantity_per_dish * ing.conversion_factor * ing.cost_per_unit) de cada ingrediente del plato.
        Retorna 0.0 si el plato no existe o no tiene ingredientes.
        """
        if not dish_name or not str(dish_name).strip():
            return 0.0

        recipe = self.get_recipe(dish_name)
        if not recipe or not recipe.ingredients:
            return 0.0

        total_cost = 0.0
        for ing in recipe.ingredients:
            qty = getattr(ing, "quantity_per_dish", 0.0) or 0.0
            factor = getattr(ing, "conversion_factor", 0.001) or 0.001
            cost_unit = getattr(ing, "cost_per_unit", 0.0) or 0.0
            total_cost += float(qty) * float(factor) * float(cost_unit)

        return float(round(total_cost, 2))

    def get_menu_engineering_df(self, sales_df: Optional[pd.DataFrame]) -> pd.DataFrame:
        """
        Genera el DataFrame de Ingeniería de Menú y Análisis de Rentabilidad (Matriz BCG).
        Calcula por cada plato:
        - Unidades Vendidas
        - Precio de Venta Promedio ($ CLP)
        - Costo de Receta ($ CLP)
        - Margen de Contribución Unitario ($ CLP)
        - Margen de Contribución (%)
        - Margen Total Acumulado ($ CLP)
        - Clasificación en Cuadrante (🌟 Estrella, 🐎 Caballo de Batalla, 🧩 Rompecabezas, 🐕 Perro)
        """
        columns = [
            "Plato",
            "Categoria_Cuadrante",
            "Precio_Venta",
            "Costo_Receta",
            "Margen_Unitario",
            "Margen_Pct",
            "Unidades_Vendidas",
            "Margen_Total"
        ]

        if sales_df is None or not isinstance(sales_df, pd.DataFrame) or sales_df.empty:
            return pd.DataFrame(columns=columns)

        # 1. Identificar columna de plato
        dish_col = None
        for col in sales_df.columns:
            clean_col = str(col).strip().lower()
            if clean_col in ["plato", "dish", "item", "producto", "articulo", "item_name", "nombre_producto", "descripcion"]:
                dish_col = col
                break
        if not dish_col:
            str_cols = sales_df.select_dtypes(include=["object", "string"]).columns
            dish_col = str_cols[0] if len(str_cols) > 0 else sales_df.columns[0]

        # 2. Identificar columna de cantidad vendida
        qty_col = None
        for col in sales_df.columns:
            clean_col = str(col).strip().lower()
            if clean_col in ["cantidad", "cant", "cantidad_vendida", "unidades", "qty", "quantity", "cant_vendida", "total_unidades"]:
                qty_col = col
                break

        # 3. Identificar columna de precio o ingreso
        price_col = None
        rev_col = None
        for col in sales_df.columns:
            clean_col = str(col).strip().lower()
            if clean_col in ["precio", "precio_venta", "precio_unitario", "unit_price", "price", "valor_unitario"]:
                price_col = col
                break
            elif clean_col in ["total", "total_venta", "ingreso", "ingreso_total", "monto", "revenue", "sales"]:
                rev_col = col
                break

        # Helper para resolver precio de venta por plato
        def _resolve_price(d_name: str, calculated_p: float, c_receta: float) -> float:
            if calculated_p > 0:
                return float(round(calculated_p, 0))

            lower_d = d_name.lower()
            if lower_d in DEFAULT_DISH_SALE_PRICES_CLP:
                return float(DEFAULT_DISH_SALE_PRICES_CLP[lower_d])

            for k, p in DEFAULT_DISH_SALE_PRICES_CLP.items():
                if k in lower_d or lower_d in k:
                    return float(p)

            # Fallback estimado con food cost target 30%
            if c_receta > 0:
                return float(max(round(c_receta / 0.30, -2), 3500.0))

            return float(DEFAULT_DISH_SALE_PRICES_CLP.get("default", 10500))

        # 4. Agrupar por plato y calcular métricas
        records = []
        for dish_val, group in sales_df.groupby(dish_col):
            d_name = str(dish_val).strip().title()
            if not d_name or d_name.lower() in ["nan", "none", "", "null"]:
                continue

            # Unidades vendidas
            if qty_col and qty_col in group.columns:
                u_series = pd.to_numeric(group[qty_col], errors="coerce").fillna(0)
                unidades = float(u_series.sum())
            else:
                unidades = float(len(group))

            if unidades <= 0:
                unidades = 1.0

            # Costo de receta
            costo_receta = self.get_recipe_cost(d_name)

            # Precio de venta
            calc_price = 0.0
            if price_col and price_col in group.columns:
                p_series = pd.to_numeric(group[price_col], errors="coerce").dropna()
                if not p_series.empty and p_series.mean() > 0:
                    calc_price = float(p_series.mean())
            elif rev_col and rev_col in group.columns:
                r_series = pd.to_numeric(group[rev_col], errors="coerce").fillna(0)
                tot_rev = float(r_series.sum())
                if tot_rev > 0 and unidades > 0:
                    calc_price = float(tot_rev / unidades)

            precio_venta = _resolve_price(d_name, calc_price, costo_receta)

            # Si el precio es menor o igual al costo de receta, calibrar con food cost target
            if costo_receta > 0 and precio_venta <= costo_receta:
                precio_venta = float(round(costo_receta / 0.30, -2))

            ventas_totales = unidades * precio_venta
            costo_total_insumos = unidades * costo_receta
            margen_unitario = precio_venta - costo_receta
            margen_pct = (margen_unitario / precio_venta * 100.0) if precio_venta > 0 else 0.0
            margen_total = margen_unitario * unidades

            records.append({
                "Plato": d_name,
                "Precio_Venta": float(round(precio_venta, 2)),
                "Costo_Receta": float(round(costo_receta, 2)),
                "Margen_Unitario": float(round(margen_unitario, 2)),
                "Margen_Pct": float(round(margen_pct, 2)),
                "Unidades_Vendidas": float(round(unidades, 1)),
                "Ventas_Totales": float(round(ventas_totales, 2)),
                "Costo_Total_Insumos": float(round(costo_total_insumos, 2)),
                "Margen_Total": float(round(margen_total, 2))
            })

        if not records:
            return pd.DataFrame(columns=columns)

        # Calcular % Mix de Ventas
        total_ventas_sum = sum(r["Ventas_Totales"] for r in records)
        for r in records:
            r["Mix_Ventas_Pct"] = float(round((r["Ventas_Totales"] / total_ventas_sum * 100.0), 2)) if total_ventas_sum > 0 else 0.0

        result_df = pd.DataFrame(records)

        # 5. Clasificación en Cuadrantes (Matriz BCG / Menú Engineering)
        mean_units = float(result_df["Unidades_Vendidas"].mean())
        mean_margin = float(result_df["Margen_Unitario"].mean())

        def _classify(row):
            high_rot = row["Unidades_Vendidas"] >= mean_units
            high_mar = row["Margen_Unitario"] >= mean_margin
            if high_rot and high_mar:
                return "🌟 Estrella"
            elif high_rot and not high_mar:
                return "🐎 Caballo de Batalla"
            elif not high_rot and high_mar:
                return "🧩 Rompecabezas"
            else:
                return "🐕 Perro"

        result_df["Categoria_Cuadrante"] = result_df.apply(_classify, axis=1)

        # Sanitización de nulos o infinitos
        result_df = result_df.fillna(0.0)
        result_df = result_df.replace([float("inf"), float("-inf")], 0.0)

        # Ordenar por Margen Total Acumulado descendente
        result_df = result_df.sort_values(by="Margen_Total", ascending=False).reset_index(drop=True)

        return result_df


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

    def update_from_dataframe(self, df: pd.DataFrame, filtered_dish: Optional[str] = None):
        """
        Reconstruye y persiste la lista de escandallos a partir de los datos editados
        en el st.data_editor de Streamlit.
        Si filtered_dish está especificado y es distinto de 'Todos los platos', actualiza
        únicamente ese plato y preserva todos los demás escandallos existentes.
        """
        if df.empty and not filtered_dish:
            return

        if filtered_dish and filtered_dish != "Todos los platos":
            clean_filtered = str(filtered_dish).strip().title()
            new_recipes: Dict[str, Recipe] = {
                k: v for k, v in self.recipes.items() if k.strip().title() != clean_filtered
            }
        else:
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
