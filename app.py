"""Punto de entrada principal de la plataforma SaaS EZtock.

Gestión inteligente de stock, compras y costos gastronómicos en Chile:
- Pestaña 1: Carga de archivo CSV (o botón para usar los datos demo generados).
- Pestaña 2: Editor interactivo de escandallos e insumos con costeo en pesos chilenos ($ CLP).
- Pestaña 3: Dashboard de recomendaciones de compra con valorización en CLP, alertas de merma y exportaciones.
"""

import streamlit as st
from src.config import APP_NAME, APP_TAGLINE, APP_VERSION
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
    if "detected_dishes" not in st.session_state:
        st.session_state["detected_dishes"] = []
    if "forecast_df" not in st.session_state:
        st.session_state["forecast_df"] = None


def main():
    st.set_page_config(
        page_title=f"{APP_NAME} | {APP_TAGLINE}",
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

    # Sidebar: Identidad EZtock y Estado de Operación
    with st.sidebar:
        st.markdown(f"### 🥑 **{APP_NAME}**")
        st.markdown(
            f"<span style='font-size: 0.85rem; color: #64748B;'>{APP_TAGLINE}.</span>",
            unsafe_allow_html=True
        )
        st.markdown("---")

        st.markdown("#### 📌 Estado de la Operación")
        has_sales = st.session_state.get("sales_df") is not None
        detected_count = len(st.session_state.get("detected_dishes", []))
        recipes_count = len(recipe_service.get_all_recipes())
        has_forecast = st.session_state.get("forecast_df") is not None

        st.markdown(f"• **Ventas POS:** {'🟢 Activas' if has_sales else '⚪ Pendiente de carga'}")
        if detected_count > 0:
            st.markdown(f"• **Platos Detectados:** 🟢 {detected_count} en carta")
        st.markdown(f"• **Escandallos:** 🟢 {recipes_count} platos costeados")
        st.markdown(f"• **Motor de Proyección:** {'🟢 Calibrado (+15%)' if has_forecast else '⚪ Listo'}")

        st.markdown("---")
        st.markdown("#### 🇨🇱 Costos y Mermas en Chile")
        st.markdown(
            "<div style='font-size: 0.82rem; color: #475569;'>"
            "• <strong>Moneda:</strong> Pesos Chilenos ($ CLP)<br>"
            "• <strong>Ahorro Típico:</strong> 12% a 15% de reducción en el costo de perecibles.<br>"
            "• <strong>Margen sugerido:</strong> 10% a 15% para evitar quiebres."
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown("---")
        st.markdown(
            f"<div style='font-size: 0.78rem; color: #94A3B8; text-align: center;'>{APP_NAME} v{APP_VERSION}<br>Santiago, Chile 🇨🇱</div>",
            unsafe_allow_html=True
        )

    # Navegación por pestañas
    tab1, tab2, tab3 = st.tabs([
        "📂 Pestaña 1: Carga de Ventas POS",
        "🥗 Pestaña 2: Editor de Escandallos ($ CLP)",
        "🛒 Pestaña 3: Dashboard de Compras & Costos"
    ])

    with tab1:
        render_pos_view(pos_parser, recipe_service)

    with tab2:
        render_recipes_view(recipe_service)

    with tab3:
        render_procurement_dashboard_view(forecasting_engine, procurement_service)


if __name__ == "__main__":
    main()
