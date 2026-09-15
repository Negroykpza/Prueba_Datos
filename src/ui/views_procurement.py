"""Vista 3: Dashboard Financiero EZtock, Métricas Primarias, Alertas Operativas y Análisis de Costos ($ CLP)."""

from datetime import timedelta
import textwrap
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from src.services.forecasting import ForecastingEngine
from src.services.procurement import ProcurementService
from src.config import APP_NAME, TAB_OPTIONS, set_active_tab
from src.ui.components import render_financial_hero_card


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
        st.error("No se pudieron generar compras. Asegúrate de tener recetas e insumos guardados en la Pestaña 2.")
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

    # 5. Alertas Operativas con Componentes Nativos de Streamlit (Zero Fugas de HTML)
    st.subheader("⚡ Alertas Operativas y Puntos de Fuga")
    st.markdown(
        "<span style='font-size: 0.92rem; color: #94A3B8;'>Decisiones operativas inmediatas para cuidar el flujo de caja y evitar botar materias primas a la basura.</span>",
        unsafe_allow_html=True
    )

    col_alert_frena, col_alert_promo = st.columns(2)

    # Tarjeta 1: 🔴 Frena Compras (Sobrestock en Bodega)
    with col_alert_frena:
        with st.container(border=True):
            col_h1, col_h2 = st.columns([2.8, 1.4])
            with col_h1:
                st.markdown("##### 🛑 Frena Compras (Sobrestock)")
            with col_h2:
                st.markdown(
                    '<span class="delta-pill delta-negative" style="float: right;">PAUSAR PEDIDOS</span>',
                    unsafe_allow_html=True
                )

            st.caption("Insumos con cobertura garantizada en bodega. **Evita compras impulsivas** que inmovilicen dinero:")

            frena_items = alerts.get("frena_compras", [])
            if frena_items:
                for item in frena_items:
                    with st.container(border=True):
                        st.markdown(f"**🛑 {item['insumo']}**")
                        st.write(item["motivo"])
                        st.caption(f"💰 Flujo de caja retenido: **{item['ahorro_estimado']}**")
            else:
                st.info("No hay órdenes que requieran pausa en este ciclo.")

    # Tarjeta 2: 🟡 Promoción Preventiva (Venta Acelerada de Perecibles < 48h)
    with col_alert_promo:
        with st.container(border=True):
            col_h1, col_h2 = st.columns([2.8, 1.4])
            with col_h1:
                st.markdown("##### 🟡 Promoción Preventiva (Menú)")
            with col_h2:
                st.markdown(
                    '<span class="delta-pill delta-warning" style="float: right;">VENTA ACELERADA</span>',
                    unsafe_allow_html=True
                )

            st.caption("Insumos perecibles críticos (< 48h). **Saca estos platos a la carta hoy** para asegurar su rotación:")

            promo_items = alerts.get("promociones", [])
            if promo_items:
                for item in promo_items:
                    with st.container(border=True):
                        col_p1, col_p2 = st.columns([3, 1.8])
                        with col_p1:
                            st.markdown(f"**🍽️ {item['insumo']}**")
                        with col_p2:
                            st.caption(f"⏳ {item['caducidad']}")
                        st.markdown(f"📌 **Sugerencia:** *{item['plato_sugerido']}*")
                        st.write(f"💡 {item['estrategia']}")
            else:
                st.info("Sin alertas críticas de caducidad en el lote proyectado.")

    # Botón CTA hacia la Pestaña 4
    st.markdown('<div class="cta-container">', unsafe_allow_html=True)
    col_spacer, col_cta = st.columns([1.4, 1.1])
    with col_cta:
        st.button(
            "Generar Órdenes por Proveedor y Enviar WhatsApp ➡️",
            type="primary",
            use_container_width=True,
            on_click=set_active_tab,
            args=(TAB_OPTIONS[3],)
        )
    st.markdown('</div>', unsafe_allow_html=True)


# Compatibilidad con cualquier importación previa
def render_procurement_dashboard_view(forecasting_engine, procurement_service):
    render_financial_dashboard_view(forecasting_engine, procurement_service)
