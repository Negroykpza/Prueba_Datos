"""Punto de entrada principal de la plataforma SaaS EZtock.

Gestión inteligente de stock, compras y costos gastronómicos en Chile:
- Pestaña 1: Carga y normalización de ventas POS (con detección automática de platos).
- Pestaña 2: Recetas e insumos por plato (ingredientes y costo de compra en $ CLP).
- Pestaña 3: Dashboard Financiero Primario: Ahorro en $ CLP, Puntos de Fuga y Food Cost Proyectado.
- Pestaña 4: Mis Proveedores: Lista de compras clasificada con botón de WhatsApp independiente y reportes.
"""

import streamlit as st
from src.config import APP_NAME, APP_TAGLINE, APP_VERSION, TAB_OPTIONS, set_active_tab
from src.services.pos_parser import POSParser
from src.services.recipe_service import RecipeService
from src.services.forecasting import ForecastingEngine
from src.services.procurement import ProcurementService
from src.ui.components import inject_custom_styles, scroll_to_top
from src.ui.views_pos import render_pos_view
from src.ui.views_recipes import render_recipes_view
from src.ui.views_procurement import render_financial_dashboard_view
from src.ui.views_suppliers import render_suppliers_view


def init_app_state():
    """Inicializa variables en el estado de sesión si no existen."""
    # Soporte para navegación pendiente vía next_tab antes del ciclo de renderizado
    if "next_tab" in st.session_state and st.session_state["next_tab"]:
        st.session_state["active_tab"] = st.session_state.pop("next_tab")

    if "active_tab" not in st.session_state or st.session_state["active_tab"] not in TAB_OPTIONS:
        st.session_state["active_tab"] = TAB_OPTIONS[0]
    if "selected_tab_name" not in st.session_state:
        st.session_state["selected_tab_name"] = TAB_OPTIONS[0]
    if "sales_df" not in st.session_state:
        st.session_state["sales_df"] = None
    if "pos_summary" not in st.session_state:
        st.session_state["pos_summary"] = None
    if "detected_dishes" not in st.session_state:
        st.session_state["detected_dishes"] = []
    if "forecast_df" not in st.session_state:
        st.session_state["forecast_df"] = None
    if "shopping_df" not in st.session_state:
        st.session_state["shopping_df"] = None
    if "restaurant_name" not in st.session_state:
        st.session_state["restaurant_name"] = "Restaurante & Bar Central"
    if "periodo_label" not in st.session_state:
        st.session_state["periodo_label"] = "Fin de Semana (Viernes a Domingo)"
    if "margen_pct" not in st.session_state:
        st.session_state["margen_pct"] = 15
    if "solo_fin_semana" not in st.session_state:
        st.session_state["solo_fin_semana"] = True


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

    # Sidebar: Identidad EZtock y Estado de Operación con Alto Contraste
    with st.sidebar:
        st.markdown(f"### 🥑 **{APP_NAME}**")
        st.markdown(
            f"<span style='font-size: 0.88rem; color: #94A3B8;'>{APP_TAGLINE}</span>",
            unsafe_allow_html=True
        )
        st.markdown("---")

        st.markdown('<div class="sidebar-section-title">📌 Estado de la Operación</div>', unsafe_allow_html=True)
        has_sales = st.session_state.get("sales_df") is not None
        detected_count = len(st.session_state.get("detected_dishes", []))
        recipes_count = len(recipe_service.get_all_recipes())
        has_forecast = st.session_state.get("forecast_df") is not None

        st.markdown(f"• **Ventas POS:** {'🟢 Activas' if has_sales else '⚪ Pendiente de carga'}")
        if detected_count > 0:
            st.markdown(f"• **Platos Detectados:** 🟢 {detected_count} en carta")
        st.markdown(f"• **Recetas:** 🟢 {recipes_count} platos costeados")
        st.markdown(f"• **Motor de Proyección:** {'🟢 Calibrado (+15%)' if has_forecast else '⚪ Listo'}")

        st.markdown("---")
        st.markdown('<div class="sidebar-section-title">🇨🇱 Costos y Mermas en Chile</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="sidebar-info-box">
                • <strong>Moneda:</strong> <span class="sidebar-highlight">Pesos Chilenos ($ CLP)</span><br>
                • <strong>Ahorro Típico:</strong> <span class="sidebar-highlight">12% a 15%</span> de reducción en compras de perecibles.<br>
                • <strong>Margen sugerido:</strong> 10% a 15% para evitar quiebres en turnos de alta demanda.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("---")
        st.markdown(
            f"<div style='font-size: 0.80rem; color: #94A3B8; text-align: center; line-height: 1.5;'>"
            f"<strong>{APP_NAME}</strong> v{APP_VERSION}<br>"
            f"Plataforma SaaS Gastronómica<br>"
            f"Santiago, Chile 🇨🇱"
            f"</div>",
            unsafe_allow_html=True
        )

    # Procesar salto de pestaña pendiente si existe
    if "next_tab" in st.session_state and st.session_state["next_tab"]:
        st.session_state["active_tab"] = st.session_state.pop("next_tab")

    # Navegación Interactiva por Pestañas (sincronización directa mediante key='active_tab')
    if "active_tab" not in st.session_state or st.session_state["active_tab"] not in TAB_OPTIONS:
        st.session_state["active_tab"] = TAB_OPTIONS[0]

    selected_tab = st.radio(
        "Navegación de Módulos:",
        options=TAB_OPTIONS,
        key="active_tab",
        horizontal=True,
        label_visibility="collapsed"
    )

    # Mantener sincronizado selected_tab_name para compatibilidad
    st.session_state["selected_tab_name"] = selected_tab

    # Renderizado condicional según la pestaña activa
    active_tab = selected_tab

    # Scroll to Top automático e imperceptible al cambiar de sección o presionar botones de avance
    last_rendered_tab = st.session_state.get("_last_rendered_tab")
    must_scroll = st.session_state.pop("trigger_scroll_top", False)
    if must_scroll or last_rendered_tab != active_tab:
        scroll_to_top()
        st.session_state["_last_rendered_tab"] = active_tab

    if active_tab == TAB_OPTIONS[0]:
        render_pos_view(pos_parser, recipe_service)
    elif active_tab == TAB_OPTIONS[1]:
        render_recipes_view(recipe_service)
    elif active_tab == TAB_OPTIONS[2]:
        render_financial_dashboard_view(forecasting_engine, procurement_service)
    elif active_tab == TAB_OPTIONS[3]:
        render_suppliers_view(forecasting_engine, procurement_service)


if __name__ == "__main__":
    main()
