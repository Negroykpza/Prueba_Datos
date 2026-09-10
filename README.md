# 🥑 GastroMerma Chile | SaaS de Reducción de Mermas Gastronómicas

> **Plataforma MVP en Python y Streamlit** diseñada para restaurantes independientes de Chile. Convierte el historial de ventas exportado desde sistemas POS (Toteat, Bsale, Fudo, Loyverse o Excel) en proyecciones inteligentes de demanda de insumos perecibles y genera la **Lista de Compras Sugerida para el Fin de Semana**, aplicando un margen de seguridad del 15% para evitar quiebres y eliminar el sobrestock.

---

## 🎯 Problema de Negocio en Chile

En el rubro gastronómico independiente chileno:
- Las mermas por alimentos vencidos o descompuestos (especialmente pescados, mariscos, carnes y verduras frescas) representan entre el **4% y 8% del Food Cost**.
- La compra para el fin de semana suele hacerse por "intuición" o repitiendo pedidos fijos a proveedores de La Vega Central, Lo Valledor o el Terminal Pesquero, generando sobrecompras críticas los días jueves/viernes que terminan en la basura los lunes.

**GastroMerma** resuelve esto automatizando la explosión de escandallos y aplicando un modelo predictivo basado en patrones reales por día de la semana.

---

## 🏗️ Arquitectura Modular del Proyecto

```text
TRABAJO_EMPRENDIMIENTO/
├── app.py                      # Punto de entrada y orquestador de Streamlit
├── requirements.txt            # Dependencias (streamlit, pandas, plotly, openpyxl)
├── README.md                   # Documentación técnica y guía de ejecución
├── data/
│   ├── sample_pos_sales.csv    # Dataset realista de 60 días (formato POS chileno)
│   └── recipes_default.json    # Escandallos base precargados (Ceviches, Lomo, Salmón, etc.)
├── src/
│   ├── __init__.py
│   ├── config.py               # Constantes: Margen de seguridad (15%), días peak, factores de unidad
│   ├── models/
│   │   ├── __init__.py
│   │   └── schema.py           # Dataclasses de dominio (Recipe, Ingredient, Sale, Forecast)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pos_parser.py       # Ingesta, detección automática de delimitador/encoding y limpieza
│   │   ├── recipe_service.py   # Gestión y persistencia de escandallos simples en JSON
│   │   ├── forecasting.py      # Motor de predicción por día de semana + 15% margen de seguridad
│   │   └── procurement.py      # Conversión de unidades (g -> kg, un -> un) y filtro de fin de semana
│   └── ui/
│       ├── __init__.py
│       ├── components.py       # Estilos CSS gastronómicos, tarjetas de KPI y banners
│       ├── views_pos.py        # Vista 1: Carga y validación de ventas POS
│       ├── views_recipes.py    # Vista 2: Gestión de escandallos
│       ├── views_forecast.py   # Vista 3: Curvas de demanda y análisis
│       └── views_procurement.py # Vista 4: Lista de compras sugerida y exportación WhatsApp/Excel
└── tests/
    ├── __init__.py
    ├── test_pos_parser.py      # Pruebas de delimitadores, fechas chilenas y agregación
    ├── test_forecasting.py     # Verificación matemática del promedio y margen del 15%
    └── test_procurement.py     # Verificación de explosión de recetas y filtro de fin de semana
```

---

## 🚀 Funcionalidades Principales

### 1. Ingesta Resiliente de Ventas POS (`src/services/pos_parser.py`)
- Detección automática de delimitador (`,` o `;`) y codificación (`UTF-8` o `Latin-1`).
- Reconocimiento automático de alias de columnas (`Fecha`/`Date`, `Plato`/`Producto`/`Item`, `Cantidad Vendida`/`Qty`).
- Normalización de fechas chilenas (`DD/MM/YYYY`) y cantidades numéricas.
- **Modo Demo en 1 clic**: Carga inmediata de un dataset de 60 días representativo para pruebas rápidas.

### 2. Escandallo Simple de Insumos Perecibles (`src/services/recipe_service.py`)
- Permite asociar cada plato a **1 o 2 insumos perecibles clave** (el 80/20 del desperdicio: reineta, salmón, lomo vacuno, cebolla morada, limón sutil, palta).
- Control de dosis por plato y factores de conversión automáticos (ej: $180\text{ g} \rightarrow 0.18\text{ kg}$).
- Persistencia local en `data/recipes.json` con opción de restablecer a recetas típicas chilenas.
- Medidor de cobertura (% de platos del POS que tienen receta definida).

### 3. Motor de Predicción con Margen de Seguridad (+15%) (`src/services/forecasting.py`)
- Calcula el promedio histórico representativo según el día de la semana (Lunes a Domingo):
  $$\text{Promedio}(plato, d) = \frac{\sum \text{Ventas}(plato, d)}{\text{Frecuencia histórica del día } d}$$
- Proyecta el consumo para los **próximos 7 días calendario**.
- Aplica el **colchón de seguridad del 15%**:
  $$\text{Demanda con Margen} = \text{Demanda Base} \times (1 + 0.15)$$
- Gráficos interactivos en Plotly: Desglose base vs margen y perfiles de venta por día de la semana.

### 4. Lista de Compras Sugerida para el Fin de Semana (`src/services/procurement.py`)
- Descompone la demanda proyectada de platos en necesidades netas de insumos perecibles.
- Filtro especializado para **Fin de Semana (Viernes, Sábado y Domingo)**, el período de mayor riesgo de merma.
- Muestra el total a comprar expresado en unidades comerciales (**kg**, **litros** o **unidades**).
- **Exportación operativa**:
  - 📲 **WhatsApp para Proveedores**: Texto formateado con emojis listo para copiar y enviar a distribuidores.
  - 📊 **Excel (.xlsx)** y **CSV (.csv)** para el equipo de compras y administración.

---

## 💻 Instalación y Ejecución Local

### Prerrequisitos
- Python 3.9 o superior instalado.

### Paso 1: Clonar o situarse en el directorio del proyecto
```bash
cd c:\Users\crist\OneDrive\Escritorio\TRABAJO_EMPRENDIMIENTO
```

### Paso 2: Crear entorno virtual (Recomendado)
```bash
python -m venv .venv
# En Windows PowerShell:
.venv\Scripts\Activate.ps1
# En Windows CMD:
.venv\Scripts\activate.bat
```

### Paso 3: Instalar dependencias
```bash
pip install -r requirements.txt
```

### Paso 4: Ejecutar la aplicación Streamlit
```bash
streamlit run app.py
```
La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`.

---

## 🧪 Ejecución de Pruebas Unitarias

Para validar la integridad de los cálculos y servicios:
```bash
python -m unittest discover tests
```

---

## 📈 Siguientes Pasos (Roadmap de Escalamiento)

1. **Integración Directa con APIs POS**: Conectores webhook a Bsale, Toteat y Fudo para ingesta en tiempo real.
2. **Alertas Climatológicas y Feriados**: Ajuste dinámico del margen de seguridad ante lluvias o feriados largos (Fiestas Patrias).
3. **Módulo de Mermas Reales (Feedback Loop)**: Registro del sobrante del lunes para ajustar el modelo con Machine Learning.
