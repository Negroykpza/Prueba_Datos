"""Vista 3: Dashboard Financiero EZtock, Métricas Primarias, Alertas Operativas y Análisis de Costos ($ CLP)."""

from typing import Optional, Any
from datetime import timedelta
import textwrap
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from src.services.forecasting import ForecastingEngine
from src.services.procurement import ProcurementService
from src.services.recipe_service import RecipeService
from src.config import APP_NAME, TAB_OPTIONS, set_active_tab
from src.ui.components import render_financial_hero_card


def render_financial_dashboard_view(
    forecasting_engine: ForecastingEngine,
    procurement_service: ProcurementService,
    recipe_service: Optional[RecipeService] = None
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

    if recipe_service is None:
        recipe_service = getattr(procurement_service, "recipe_service", None)
    if recipe_service is None:
        recipe_service = RecipeService()

    tab_abast, tab_menu = st.tabs(["📦 Abastecimiento y Fugas", "📈 Rentabilidad e Ingeniería de Menú"])

    with tab_abast:
        # 1. Controles Superiores de Gestión y Simulación
        col_c1, col_c2, col_c3 = st.columns([1.2, 1.2, 1.2])

        with col_c1:
            if "periodo_abastecimiento" not in st.session_state:
                st.session_state.periodo_abastecimiento = "🎯 Solo Fin de Semana (Vie - Sáb - Dom)"

            filtro_horizonte = st.radio(
                "📅 Período de Abastecimiento:",
                options=["🎯 Solo Fin de Semana (Vie - Sáb - Dom)", "🗓️ Próximos 7 Días Corridos"],
                key="periodo_abastecimiento",
                help="En Chile, la mayor demanda de perecibles se concentra de viernes a domingo."
            )
            solo_fin_semana = (filtro_horizonte == "🎯 Solo Fin de Semana (Vie - Sáb - Dom)")
            periodo_label = "Fin de Semana (Viernes a Domingo)" if solo_fin_semana else "Próximos 7 Días Corridos"
            st.session_state["periodo_label"] = periodo_label
            st.session_state["solo_fin_semana"] = solo_fin_semana

        with col_c2:
            if "safety_margin" not in st.session_state:
                st.session_state["safety_margin"] = 15

            margen_pct = st.slider(
                "🛡️ Margen de Seguridad (%):",
                min_value=5,
                max_value=25,
                step=1,
                key="safety_margin",
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

        # 5. Alertas Operativas simplificadas (diseño nativo con st.container(border=True))
        st.subheader("⚡ Alertas Operativas y Puntos de Fuga")
        st.markdown(
            "<span style='font-size: 0.92rem; color: #94A3B8;'>Decisiones operativas inmediatas para proteger el flujo de caja y evitar mermas.</span>",
            unsafe_allow_html=True
        )

        col_alert_frena, col_alert_promo = st.columns(2)

        # Tarjeta 1: 🛑 Frena Compras (Sobrestock en Bodega)
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

                st.caption("Insumos con stock cubierto en bodega. **Evita compras impulsivas**:")

                frena_items = alerts.get("frena_compras", [])
                if frena_items:
                    for item in frena_items:
                        with st.container(border=True):
                            st.markdown(f"**🛑 {item['insumo']}**")
                            st.write(f"👉 **Acción sugerida:** {item['motivo']}")
                            st.caption(f"💰 Capital protegido / Flujo retenido: **{item['ahorro_estimado']}**")
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

                st.caption("Insumos perecibles críticos (< 48h). **Promueve estos platos hoy** para rotar stock:")

                promo_items = alerts.get("promociones", [])
                if promo_items:
                    for item in promo_items:
                        with st.container(border=True):
                            col_p1, col_p2 = st.columns([3, 1.8])
                            with col_p1:
                                st.markdown(f"**🍽️ {item['insumo']}**")
                            with col_p2:
                                st.caption(f"⏳ {item['caducidad']}")
                            st.markdown(f"👉 **Plato sugerido:** *{item['plato_sugerido']}*")
                            st.write(f"💡 **Estrategia:** {item['estrategia']}")
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

    with tab_menu:
        # =========================================================================
        # RENTABILIDAD DE RECETAS E INGENIERÍA DE MENÚ (MATRIZ BCG)
        # =========================================================================
        st.subheader("📈 Rentabilidad de Recetas e Ingeniería de Menú")
        st.markdown(
            "<span style='font-size: 0.92rem; color: #94A3B8;'>Análisis estratégico de popularidad (rotación) vs. margen de contribución unitario para optimizar la rentabilidad de la carta.</span>",
            unsafe_allow_html=True
        )

        menu_df = recipe_service.get_menu_engineering_df(sales_df)
        if not menu_df.empty:
            # 1. Cuatro Métricas Clave en Columnas
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)

            total_billing = float(menu_df["Ventas_Totales"].sum())
            total_margin = float(menu_df["Margen_Total"].sum())
            avg_margin_pct = float(menu_df["Margen_Pct"].mean())

            # Facturación Total Estimada ($ CLP)
            with col_m1:
                st.metric(
                    "Facturación Total Estimada ($ CLP)",
                    f"${int(total_billing):,} CLP".replace(",", "."),
                    help="Ingreso total estimado por venta de platos en el histórico analizado."
                )

            # Margen Total Acumulado ($ CLP)
            with col_m2:
                st.metric(
                    "Margen Total Acumulado ($ CLP)",
                    f"${int(total_margin):,} CLP".replace(",", "."),
                    help="Ganancia bruta total generada (Ventas Totales - Costo Total Insumos)."
                )

            # Margen Contribución Promedio (%)
            with col_m3:
                st.metric(
                    "Margen Contribución Promedio (%)",
                    f"{avg_margin_pct:.1f}%",
                    help="Promedio porcentual del margen sobre el precio de venta en todos los platos analizados."
                )

            # Plato Estrella (nombre del plato líder)
            star_df = menu_df[menu_df["Categoria_Cuadrante"] == "🌟 Estrella"]
            with col_m4:
                if not star_df.empty:
                    top_star = star_df.loc[star_df["Margen_Total"].idxmax()]
                    st.metric(
                        "Plato Estrella",
                        top_star["Plato"],
                        delta=f"${int(top_star['Margen_Unitario']):,} CLP / plato".replace(",", "."),
                        help="Plato líder en el cuadrante de alta rotación y alto margen de contribución."
                    )
                else:
                    top_overall = menu_df.iloc[0]
                    st.metric(
                        "Plato Estrella",
                        top_overall["Plato"],
                        delta=f"${int(top_overall['Margen_Unitario']):,} CLP".replace(",", "."),
                        help="Plato con mayor contribución individual."
                    )

            st.markdown("---")

            # 2. Gráfico Scatter Plot interactivo con Plotly
            mean_u = float(menu_df["Unidades_Vendidas"].mean())
            mean_m = float(menu_df["Margen_Unitario"].mean())

            fig_menu = go.Figure()

            quadrant_configs = [
                ("🌟 Estrella", "#10B981", "star", 15),
                ("🐎 Caballo de Batalla", "#38BDF8", "square", 12),
                ("🧩 Rompecabezas", "#F59E0B", "diamond", 12),
                ("🐕 Perro", "#EF4444", "circle", 11)
            ]

            for cat_name, color, symbol, size in quadrant_configs:
                sub_df = menu_df[menu_df["Categoria_Cuadrante"].str.startswith(cat_name[:4])]
                if sub_df.empty:
                    continue

                hover_texts = []
                for _, r in sub_df.iterrows():
                    p_v = f"${int(r['Precio_Venta']):,} CLP".replace(",", ".")
                    c_r = f"${int(r['Costo_Receta']):,} CLP".replace(",", ".")
                    m_u = f"${int(r['Margen_Unitario']):,} CLP".replace(",", ".")
                    m_p = f"{r['Margen_Pct']:.1f}%"
                    u_v = f"{int(r['Unidades_Vendidas']):,} un".replace(",", ".")
                    m_t = f"${int(r['Margen_Total']):,} CLP".replace(",", ".")
                    v_t = f"${int(r['Ventas_Totales']):,} CLP".replace(",", ".")
                    mix_p = f"{r.get('Mix_Ventas_Pct', 0.0):.1f}%"
                    hover_texts.append(
                        f"<b>{r['Plato']}</b><br>"
                        f"• Cuadrante: <b>{r['Categoria_Cuadrante']}</b><br>"
                        f"• Precio Venta: <b>{p_v}</b><br>"
                        f"• Costo Receta: <b>{c_r}</b><br>"
                        f"• Margen Unitario: <b>{m_u}</b> ({m_p})<br>"
                        f"• Unidades Vendidas: <b>{u_v}</b> (Mix: {mix_p})<br>"
                        f"• Ventas Totales: <b>{v_t}</b><br>"
                        f"• Margen Total: <b>{m_t}</b>"
                    )

                fig_menu.add_trace(go.Scatter(
                    x=sub_df["Unidades_Vendidas"],
                    y=sub_df["Margen_Unitario"],
                    mode="markers+text",
                    name=cat_name,
                    text=sub_df["Plato"],
                    textposition="top center",
                    textfont=dict(size=10, color="#CBD5E1"),
                    marker=dict(
                        color=color,
                        symbol=symbol,
                        size=size,
                        line=dict(width=1.5, color="#F8FAFC")
                    ),
                    hovertext=hover_texts,
                    hovertemplate="%{hovertext}<extra></extra>"
                ))

            # Líneas guía de corte en la media de ventas y margen
            fig_menu.add_vline(
                x=mean_u,
                line_dash="dot",
                line_color="#94A3B8",
                line_width=1.5,
                annotation_text=f"Media Ventas ({mean_u:.0f} un)",
                annotation_position="top right",
                annotation_font=dict(color="#94A3B8", size=10)
            )
            fig_menu.add_hline(
                y=mean_m,
                line_dash="dot",
                line_color="#94A3B8",
                line_width=1.5,
                annotation_text=f"Media Margen (${int(mean_m):,} CLP)".replace(",", "."),
                annotation_position="bottom right",
                annotation_font=dict(color="#94A3B8", size=10)
            )

            fig_menu.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#CBD5E1"),
                margin=dict(l=30, r=30, t=35, b=40),
                height=480,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5,
                    bgcolor="rgba(15,23,42,0.75)",
                    bordercolor="#334155",
                    borderwidth=1
                ),
                xaxis=dict(
                    title="Unidades Vendidas (Popularidad / Rotación)",
                    gridcolor="#334155",
                    zerolinecolor="#334155"
                ),
                yaxis=dict(
                    title="Margen de Contribución Unitario ($ CLP)",
                    gridcolor="#334155",
                    zerolinecolor="#334155",
                    tickformat="$,d"
                )
            )

            st.plotly_chart(fig_menu, use_container_width=True)

            # 3. Tabla interactiva formateada con st.dataframe
            st.markdown("##### 📋 Matriz Detallada de Rentabilidad por Plato")
            table_df = pd.DataFrame({
                "Plato": menu_df["Plato"],
                "Cuadrante": menu_df["Categoria_Cuadrante"],
                "Unidades Vendidas": menu_df["Unidades_Vendidas"].apply(lambda v: f"{int(v):,} un".replace(",", ".")),
                "Precio Venta": menu_df["Precio_Venta"].apply(lambda v: f"${int(v):,} CLP".replace(",", ".")),
                "Ventas Totales ($ CLP)": menu_df["Ventas_Totales"].apply(lambda v: f"${int(v):,} CLP".replace(",", ".")),
                "Costo Receta": menu_df["Costo_Receta"].apply(lambda v: f"${int(v):,} CLP".replace(",", ".")),
                "Costo Total Insumos ($ CLP)": menu_df["Costo_Total_Insumos"].apply(lambda v: f"${int(v):,} CLP".replace(",", ".")),
                "Margen Total ($ CLP)": menu_df["Margen_Total"].apply(lambda v: f"${int(v):,} CLP".replace(",", ".")),
                "Margen (%)": menu_df["Margen_Pct"].apply(lambda v: f"{v:.1f}%"),
                "% Mix Ventas": menu_df["Mix_Ventas_Pct"].apply(lambda v: f"{v:.1f}%")
            })

            st.dataframe(
                table_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("ℹ️ Sube un archivo de ventas en la Pestaña 1 para generar el análisis de Ingeniería de Menú.")


# Compatibilidad con cualquier importación previa
def render_procurement_dashboard_view(forecasting_engine, procurement_service):
    render_financial_dashboard_view(forecasting_engine, procurement_service)
