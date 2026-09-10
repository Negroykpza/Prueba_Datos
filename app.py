"""Punto de entrada principal de la plataforma SaaS GastroMerma Chile.

Estructura de la aplicación en 3 pestañas principales:
- Pestaña 1: Carga de archivo CSV (o botón para usar los datos demo generados).
- Pestaña 2: Configuración de recetas para los 5 insumos perecibles más críticos.
- Pestaña 3: Dashboard de recomendaciones de compra con alertas de merma estimada y exportación a WhatsApp / PDF.
"""

import streamlit as st
from src.services.pos_parser import POSParser
from src.services.recipe_service import RecipeService
from src.services.forecasting import ForecastingEngine
from src.services.procurement import ProcurementService
from src.ui.components import inject_custom_styles
from src.ui.views_pos import render_pos_view
from src.ui.views_recipes import render_recipes_view
from src.ui.views_procurement import render_procurement_dashboard_view


def init_app_state():
    """Inicializa variables en el estado de sesión si no existen."""
    if "sales_df" not in st.session_state:
        st.session_state["sales_df"] = None
    if "pos_summary" not in st.session_state:
        st.session_state["pos_summary"] = None
    if "forecast_df" not in st.session_state:
        st.session_state["forecast_df"] = None


def main():
    st.set_page_config(
        page_title="GastroMerma Chile | SaaS Reducción de Mermas",
        page_icon="🥑",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    inject_custom_styles()
    init_app_state()

    # Inicializar servicios del núcleo
    pos_parser = POSParser()
    recipe_service = RecipeService()
    forecasting_engine = ForecastingEngine()
    procurement_service = ProcurementService(recipe_service)

    # Sidebar informativo y estado de la operación
    with st.sidebar:
        st.markdown("### 🥑 **GastroMerma Chile**")
        st.markdown(
            "<span style='font-size: 0.85rem; color: #64748B;'>SaaS para restaurantes independientes enfocado en optimizar el abastecimiento y liquidar el Food Cost residual.</span>",
            unsafe_allow_html=True
        )
        st.markdown("---")

        st.markdown("#### 📌 Estado de la Operación")
        has_sales = st.session_state.get("sales_df") is not None
        recipes_count = len(recipe_service.get_all_recipes())
        has_forecast = st.session_state.get("forecast_df") is not None

        st.markdown(f"• **Ventas POS:** {'🟢 90 Días Cargados' if has_sales else '⚪ Pendiente de carga'}")
        st.markdown(f"• **Escandallos Activos:** 🟢 {recipes_count} platos configurados")
        st.markdown(f"• **Motor de Proyección:** {'🟢 Calibrado (+15%)' if has_forecast else '⚪ Listo para proyectar'}")

        st.markdown("---")
        st.markdown("#### 🇨🇱 Mercado Gastronómico")
        st.markdown(
            "<div style='font-size: 0.82rem; color: #475569;'>"
            "• <strong>Peaks en Chile:</strong> Viernes y sábado duplican las ventas respecto a lunes/martes.<br>"
            "• <strong>Mermas típicas:</strong> 4% a 8% del Food Cost se bota los lunes por sobrestock de fin de semana.<br>"
            "• <strong>Margen seguro:</strong> +15% de stock anti-quiebres."
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown("---")
        st.markdown(
            "<div style='font-size: 0.78rem; color: #94A3B8; text-align: center;'>GastroMerma v0.1.0 MVP<br>Santiago, Chile 🇨🇱</div>",
            unsafe_allow_html=True
        )

    # Navegación por pestañas principales
    tab1, tab2, tab3 = st.tabs([
        "📂 Pestaña 1: Carga de Ventas POS",
        "🥗 Pestaña 2: Escandallo (5 Insumos Críticos)",
        "🛒 Pestaña 3: Dashboard de Compras & Mermas"
    ])

    with tab1:
        render_pos_view(pos_parser)

    with tab2:
        render_recipes_view(recipe_service)

    with tab3:
        render_procurement_dashboard_view(forecasting_engine, procurement_service)


if __name__ == "__main__":
    main()
