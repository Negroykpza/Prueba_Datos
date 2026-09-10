"""Configuración general y constantes de la plataforma SaaS de reducción de mermas."""

from pathlib import Path

# Rutas de almacenamiento y datos
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_RECIPES_PATH = DATA_DIR / "recipes_default.json"
ACTIVE_RECIPES_PATH = DATA_DIR / "recipes.json"
SAMPLE_POS_PATH = DATA_DIR / "sample_pos_sales.csv"

# Parámetros del motor de proyección
DEFAULT_SAFETY_MARGIN = 0.15  # 15% margen de seguridad por defecto
FORECAST_DAYS_HORIZON = 7     # Próximos 7 días de horizonte de proyección

# Días de la semana en español (orden estándar ISO: 0 = Lunes, 6 = Domingo)
DAYS_OF_WEEK_ES = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo"
}

# Definición del fin de semana gastronómico en Chile (peak operativo: Viernes a Domingo)
WEEKEND_DAY_INDICES = [4, 5, 6]
WEEKEND_DAYS_ES = ["Viernes", "Sábado", "Domingo"]

# Mapeo de factores de conversión entre unidades de receta y unidades de compra
UNIT_CONVERSION_FACTORS = {
    ("g", "kg"): 0.001,
    ("kg", "kg"): 1.0,
    ("ml", "L"): 0.001,
    ("L", "L"): 1.0,
    ("un", "un"): 1.0,
    ("unidad", "un"): 1.0,
    ("unidades", "un"): 1.0
}

# Alias comunes de columnas en sistemas POS chilenos (Toteat, Bsale, Fudo, Loyverse, Excel)
POS_COLUMN_ALIASES = {
    "fecha": ["fecha", "date", "dia", "fec_venta", "fechaventa", "timestamp"],
    "plato": ["plato", "item", "producto", "descripcion", "articulo", "item_name", "nombre_producto"],
    "cantidad": ["cantidad", "cant", "cantidad_vendida", "unidades", "qty", "quantity", "cant_vendida", "total_unidades"]
}
