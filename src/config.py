"""Configuración general y constantes de la plataforma SaaS EZtock."""

from pathlib import Path

# Identidad de Marca
APP_NAME = "EZtock"
APP_TAGLINE = "Control Inteligente de Stock y Costos Gastronómicos"
APP_VERSION = "1.0.0"

# Rutas de almacenamiento y datos
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_RECIPES_PATH = DATA_DIR / "recipes_default.json"
ACTIVE_RECIPES_PATH = DATA_DIR / "recipes.json"
SAMPLE_POS_PATH = DATA_DIR / "sample_pos_sales.csv"

# Parámetros del motor de proyección
DEFAULT_SAFETY_MARGIN = 0.15  # 15% margen de seguridad recomendado
FORECAST_DAYS_HORIZON = 7     # 7 días horizonte de proyección

# Precios referenciales de compra en ferias mayoristas de Chile (CLP)
DEFAULT_INGREDIENT_PRICES_CLP = {
    "pescado blanco": 9500,     # Reineta / Corvina fresca por kg
    "reineta": 9500,
    "salmón": 14000,            # Filete salmón fresco por kg
    "salmon": 14000,
    "lomo": 9800,               # Lomo liso vacuno por kg
    "vacuno": 9800,
    "posta": 8800,              # Posta vacuno por kg
    "pollo": 4800,              # Pechuga de pollo por kg
    "atún": 13500,              # Atún fresco por kg
    "machas": 8500,             # Machas frescas por kg
    "cebolla": 1200,            # Cebolla morada por kg
    "limón": 1800,              # Limón sutil por malla / kg
    "limon": 1800,
    "palta": 4500,              # Palta Hass por kg
    "choclo": 2200,             # Pasta de choclo por kg
    "tomate": 1500,             # Tomate por kg
    "espárrago": 4200,          # Espárragos por kg
    "esparrago": 4200,
    "zapallo": 1400,            # Zapallo camote por kg
    "queso": 8900,              # Queso parmesano por kg
    "default": 6500             # Costo base referencial por kg o un
}

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
