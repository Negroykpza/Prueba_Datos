"""Vista 3: Dashboard Financiero EZtock, Métricas Primarias, Alertas Operativas y Análisis de Costos ($ CLP)."""

from datetime import timedelta
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from src.services.forecasting import ForecastingEngine
from src.services.procurement import ProcurementService
from src.config import APP_NAME, APP_TAGLINE
from src.ui.components import render_financial_hero_card, render_info_banner


def render_financial_dashboard_view(
    forecasting_engine: ForecastingEngine,
    procurement_service: ProcurementService
):
    """Renderiza el Dashboard Financiero Primario (Pestaña 3)."""
    st.markdown(f'<div class="main-header">💰 Dashboard Financiero & Fugas ($ CLP) | {APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Métricas financieras clave, control de mermas críticas y decisiones operativas en tiempo real.</div>',
        unsafe_allow_html=True
    )

    sales_df = st.session_state.get("sales_df")
    if sales_df is None or sales_df.empty:
        st.warning("⚠️ Para ver las métricas financieras, primero sube tu archivo CSV o presiona 'Usar Datos Demo de 90 Días' en la Pestaña 1.")
        return

    # 1. Controles Superiores de Gestión y Simulación
    col_c1, col_c2, col_c3 = st.columns([1.2, 1.2, 1.2])

    with col_c1:
        filtro_horizonte = st.radio(
            "📅 Período de Abastecimiento:",
            options=["🎯 Solo Fin de Semana (Vie - Sáb - Dom)", "🗓️ Próximos 7 Días Corridos"],
            index=0 if st.session_state.get("solo_fin_semana", True) else 1,
            help="En Chile, la mayor demanda de perecibles se concentra de viernes a domingo."
        )
        solo_fin_semana = (filtro_horizonte == "🎯 Solo Fin de Semana (Vie - Sáb - Dom)")
        periodo_label = "Fin de Semana (Viernes a Domingo)" if solo_fin_semana else "Próximos 7 Días Corridos"
        st.session_state["periodo_label"] = periodo_label
        st.session_state["solo_fin_semana"] = solo_fin_semana

    with col_c2:
        margen_pct = st.slider(
            "🛡️ Margen de Seguridad (%):",
            min_value=5,
            max_value=25,
            value=st.session_state.get("margen_pct", 15),
            step=1,
            help="Colchón operativo para evitar quiebres de stock. Rango estándar recomendado: 10% a 15%."
        )
        st.session_state["margen_pct"] = margen_pct
        safety_margin_decimal = margen_pct / 100.0

    with col_c3:
        restaurant_name = st.text_input(
            "🏪 Nombre de tu Restaurante:",
            value=st.session_state.get("restaurant_name", "Restaurante & Bar Central"),
            help="Aparecerá en el encabezado de los pedidos de WhatsApp y reportes."
        )
        st.session_state["restaurant_name"] = restaurant_name

    # 2. Proyección y Generación de Compras
    max_date = pd.to_datetime(sales_df["fecha"]).dt.date.max()
    start_date = max_date + timedelta(days=1)

    forecast_df = forecasting_engine.project_next_days(
        sales_df,
        start_date=start_date,
        days_horizon=7,
        safety_margin=safety_margin_decimal
    )
    st.session_state["forecast_df"] = forecast_df

    shopping_df = procurement_service.calculate_shopping_list(forecast_df, only_weekend=solo_fin_semana)
    st.session_state["shopping_df"] = shopping_df

    if shopping_df.empty:
        st.error("No se pudieron generar compras. Asegúrate de tener escandallos e insumos guardados en la Pestaña 2.")
        return

    # 3. Métricas Financieras Primarias
    fin_kpis = procurement_service.calculate_financial_kpis(shopping_df, forecast_df, is_weekend_only=solo_fin_semana)
    alerts = procurement_service.get_operational_alerts(shopping_df)

    ahorro_mes_str = f"${int(fin_kpis['ahorro_mes_clp']):,}".replace(",", ".")
    puntos_fuga_str = f"${int(fin_kpis['puntos_fuga_clp']):,}".replace(",", ".")
    total_orden_str = f"${int(fin_kpis['total_orden_clp']):,}".replace(",", ".")
    ventas_est_str = f"${int(fin_kpis['ventas_proyectadas_clp']):,}".replace(",", ".")

    st.markdown("---")
    st.subheader("💵 Métricas Financieras Primarias")

    c_kpi1, c_kpi2, c_kpi3 = st.columns(3)

    with c_kpi1:
        render_financial_hero_card(
            title="Ahorro Comprobado del Mes ($ CLP)",
            value=f"{ahorro_mes_str} CLP",
            caption="Diferencia real entre compras intuitivas sin control y compras optimizadas.",
            accent_color="#34D399",
            badge_text="🟢 +15% EFICIENCIA"
        )

    with c_kpi2:
        render_financial_hero_card(
            title="Puntos de Fuga de Dinero ($ CLP)",
            value=f"{puntos_fuga_str} CLP",
            caption="Capital en insumos perecibles (<48h) en riesgo de merma si no se rota a tiempo.",
            accent_color="#F87171",
            badge_text="🔴 CAPITAL EN RIESGO"
        )

    with c_kpi3:
        food_cost_pct = fin_kpis['food_cost_pct']
        accent = "#38BDF8" if 25 <= food_cost_pct <= 35 else "#FBBF24"
        render_financial_hero_card(
            title="Food Cost Proyectado (%)",
            value=f"{food_cost_pct:.1f}%",
            caption=f"Inversión de {total_orden_str} CLP sobre ventas estimadas de {ventas_est_str} CLP.",
            accent_color=accent,
            badge_text="🎯 RANGO ÓPTIMO (28% - 32%)"
        )

    st.markdown("---")

    # 4. Visualización de Inversión y Costos (Plotly)
    st.subheader("📊 Distribución de Inversión por Insumo Crítico")

    top_cost_items = shopping_df.sort_values(by="subtotal_cost_clp", ascending=False).head(8)
    if not top_cost_items.empty:
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Bar(
            x=top_cost_items["subtotal_cost_clp"],
            y=top_cost_items["insumo"],
            orientation="h",
            marker=dict(
                color=top_cost_items["subtotal_cost_clp"],
                colorscale="Teal",
                showscale=False
            ),
            text=[f"${int(v):,} CLP".replace(",", ".") for v in top_cost_items["subtotal_cost_clp"]],
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>Inversión: %{text}<extra></extra>"
        ))
        fig_cost.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#CBD5E1"),
            margin=dict(l=20, r=20, t=30, b=20),
            height=300,
            yaxis=dict(autorange="reversed", gridcolor="#334155"),
            xaxis=dict(gridcolor="#334155", tickformat="$,d")
        )
        st.plotly_chart(fig_cost, use_container_width=True)

    st.markdown("---")

    # 5. Alertas Operativas y Decisiones Inmediatas en Dark Mode
    st.subheader("⚡ Alertas Operativas y Puntos de Fuga")
    st.markdown(
        "<span style='font-size: 0.92rem; color: #94A3B8;'>Decisiones operativas inmediatas para cuidar el flujo de caja y evitar botar materias primas a la basura.</span>",
        unsafe_allow_html=True
    )

    col_alert_frena, col_alert_promo = st.columns(2)

    # Tarjeta 1: 🔴 Frena Compras (Sobrestock en Bodega)
    with col_alert_frena:
        frena_items_html = ""
        for item in alerts["frena_compras"]:
            frena_items_html += f"""
                <div class="alert-item-box">
                    <div style="font-weight: 700; color: #F87171; font-size: 0.92rem;">
                        🛑 {item['insumo']}
                    </div>
                    <div style="font-size: 0.84rem; color: #CBD5E1; margin-top: 3px; line-height: 1.4;">
                        {item['motivo']}
                    </div>
                    <div style="font-size: 0.78rem; font-weight: 600; color: #34D399; margin-top: 4px;">
                        💰 Flujo de caja retenido: {item['ahorro_estimado']}
                    </div>
                </div>
            """

        st.markdown(f"""
            <div class="alert-card-dark alert-card-danger" style="min-height: 290px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                    <span style="font-size: 1.05rem; font-weight: 800; color: #FCA5A5;">
                        🔴 Frena Compras (Sobrestock en Bodega)
                    </span>
                    <span class="delta-pill delta-negative">
                        PAUSAR PEDIDOS
                    </span>
                </div>
                <div style="font-size: 0.85rem; color: #FECACA; margin-bottom: 12px;">
                    Insumos con cobertura garantizada en bodega. <strong>Evita compras impulsivas</strong> que inmovilicen dinero:
                </div>
                {frena_items_html}
            </div>
        """, unsafe_allow_html=True)

    # Tarjeta 2: 🟡 Promoción Preventiva (Venta Acelerada de Perecibles < 48h)
    with col_alert_promo:
        promo_items_html = ""
        for item in alerts["promociones"]:
            promo_items_html += f"""
                <div class="alert-item-box">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: #FBBF24; font-size: 0.92rem;">
                            🍽️ {item['insumo']}
                        </span>
                        <span style="font-size: 0.75rem; color: #FDE68A; font-weight: 600;">
                            ⏳ {item['caducidad']}
                        </span>
                    </div>
                    <div style="font-size: 0.84rem; font-weight: 600; color: #F8FAFC; margin-top: 4px;">
                        📌 {item['plato_sugerido']}
                    </div>
                    <div style="font-size: 0.80rem; color: #CBD5E1; margin-top: 2px; line-height: 1.35;">
                        💡 {item['estrategia']}
                    </div>
                </div>
            """

        st.markdown(f"""
            <div class="alert-card-dark alert-card-warning" style="min-height: 290px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                    <span style="font-size: 1.05rem; font-weight: 800; color: #FDE68A;">
                        🟡 Promoción Preventiva (Menú del Día)
                    </span>
                    <span class="delta-pill delta-warning">
                        VENTA ACELERADA
                    </span>
                </div>
                <div style="font-size: 0.85rem; color: #FEF3C7; margin-bottom: 12px;">
                    Insumos perecibles críticos (&lt; 48h). <strong>Saca estos platos a la carta hoy</strong> para asegurar su rotación:
                </div>
                {promo_items_html}
            </div>
        """, unsafe_allow_html=True)

    # Botón CTA hacia la Pestaña 4
    st.markdown('<div class="cta-container">', unsafe_allow_html=True)
    col_spacer, col_cta = st.columns([1.4, 1.1])
    with col_cta:
        if st.button("Generar Órdenes por Proveedor y Enviar WhatsApp ➡️", type="primary", use_container_width=True):
            st.session_state["selected_tab_name"] = "🚚 4. Mis Proveedores (Compras & WhatsApp)"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# Compatibilidad con cualquier importación previa
def render_procurement_dashboard_view(forecasting_engine, procurement_service):
    render_financial_dashboard_view(forecasting_engine, procurement_service)
