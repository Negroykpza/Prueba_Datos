"""Definición de entidades y modelos de datos para la gestión de escandallos, ventas y compras."""

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import List, Dict, Any, Optional
from src.config import UNIT_CONVERSION_FACTORS


@dataclass
class IngredientRequirement:
    """Representa el requerimiento de un insumo perecible dentro de un escandallo."""
    ingredient_name: str
    quantity_per_dish: float
    recipe_unit: str = "g"        # 'g', 'ml', 'un'
    purchase_unit: str = "kg"     # 'kg', 'L', 'un'
    conversion_factor: float = 0.001  # factor para convertir recipe_unit a purchase_unit

    def __post_init__(self):
        # Autoasignar factor de conversión estándar si no se especificó uno personalizado
        key = (self.recipe_unit.lower(), self.purchase_unit.lower())
        if key in UNIT_CONVERSION_FACTORS and self.conversion_factor == 0.001 and key != ("g", "kg"):
            self.conversion_factor = UNIT_CONVERSION_FACTORS[key]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IngredientRequirement":
        return cls(
            ingredient_name=str(data["ingredient_name"]),
            quantity_per_dish=float(data["quantity_per_dish"]),
            recipe_unit=str(data.get("recipe_unit", "g")),
            purchase_unit=str(data.get("purchase_unit", "kg")),
            conversion_factor=float(data.get("conversion_factor", 0.001))
        )


@dataclass
class Recipe:
    """Escandallo (receta base) de un plato con sus insumos perecibles clave."""
    dish_name: str
    categoria: str = "General"
    ingredients: List[IngredientRequirement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dish_name": self.dish_name,
            "categoria": self.categoria,
            "ingredients": [ing.to_dict() for ing in self.ingredients]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Recipe":
        ingredients = [
            IngredientRequirement.from_dict(ing) for ing in data.get("ingredients", [])
        ]
        return cls(
            dish_name=str(data["dish_name"]),
            categoria=str(data.get("categoria", "General")),
            ingredients=ingredients
        )


@dataclass
class SaleRecord:
    """Registro individual o agregado de venta desde sistema POS."""
    fecha: date
    plato: str
    cantidad: float
    dia_semana_num: int
    dia_semana_nombre: str


@dataclass
class DishForecast:
    """Proyección de demanda para un plato en una fecha específica."""
    plato: str
    fecha_proyectada: date
    dia_semana_num: int
    dia_semana_nombre: str
    es_fin_de_semana: bool
    demanda_base: float
    margen_seguridad_pct: float
    demanda_con_margen: float


@dataclass
class ProcurementItem:
    """Línea de la lista de compras sugerida para un insumo perecible."""
    ingredient_name: str
    consumo_base: float
    margen_seguridad: float
    total_sugerido: float
    unidad_compra: str
    platos_asociados: List[str] = field(default_factory=list)
