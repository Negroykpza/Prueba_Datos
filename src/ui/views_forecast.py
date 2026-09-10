"""Vista 3: Motor de predicción de demanda de platos para los próximos 7 días."""

from datetime import timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.services.forecasting import ForecastingEngine
from src.config import DAYS_OF_WEEK_ES
from src.ui.components import render_metric_card, render_info_banner


def render_forecast_view(forecasting_engine: ForecastingEngine):
    st.markdown('<div class="main-header">📈 Motor de Predicción de Demanda</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Cálculo estadístico de consumo esperado para los próximos 7 días basado en promedios por día de la semana con margen de seguridad del 15%.</div>',
        unsafe_allow_html=True
    )

    sales_df = st.session_state.get("sales_df")
    if sales_df is None or sales_df.empty:
        st.warning("⚠️ Primero debes cargar un archivo de ventas en la pestaña '1. Carga de Ventas POS' o activar los datos demo.")
        return

    # Controles del motor de predicción
    col_par1, col_par2 = st.columns([1, 1])

    with col_par1:
        margen_pct = st.slider(
            "🛡️ Margen de Seguridad Operativo (%):",
            min_value=0,
            max_value=30,
            value=15,
            step=1,
            help="Colchón extra para evitar quiebres de stock ante peaks inesperados. La industria gastronómica recomienda 15%."
        )

    with col_par2:
        max_date = pd.to_datetime(sales_df["fecha"]).dt.date.max()
        start_date_default = max_date + timedelta(days=1)
        fecha_inicio = st.date_input(
            "📅 Fecha de Inicio de Proyección (Próximos 7 días):",
            value=start_date_default
        )

    safety_margin_decimal = margen_pct / 100.0

    # Ejecutar proyección
    forecast_df = forecasting_engine.project_next_days(
        sales_df,
        start_date=fecha_inicio,
        days_horizon=7,
        safety_margin=safety_margin_decimal
    )
    st.session_state["forecast_df"] = forecast_df
    st.session_state["safety_margin_used"] = margen_pct

    # KPIs de la proyección
    total_base = forecast_df["demanda_base"].sum()
    total_margen = forecast_df["margen_seguridad_unidades"].sum()
    total_proyectado = forecast_df["demanda_con_margen"].sum()
    fin_semana_total = forecast_df[forecast_df["es_fin_de_semana"]]["demanda_con_margen"].sum()
    pct_fin_semana = round((fin_semana_total / total_proyectado * 100), 1) if total_proyectado > 0 else 0

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_metric_card(
            "Demanda Base 7 Días",
            f"{int(total_base):,} un".replace(",", "."),
            caption="Promedio histórico puro"
        )
    with k2:
        render_metric_card(
            f"Margen Seguridad (+{margen_pct}%)",
            f"+{int(total_margen):,} un".replace(",", "."),
            caption="Colchón anti-quiebres"
        )
    with k3:
        render_metric_card(
            "Total Proyectado 7 Días",
            f"{int(total_proyectado):,} un".replace(",", "."),
            caption="Demanda sugerida con margen"
        )
    with k4:
        render_metric_card(
            "Concentración Fin de Semana",
            f"{pct_fin_semana}%",
            caption="Viernes, Sábado y Domingo",
            delta_color="#F59E0B"
        )

    st.markdown("---")

    # Gráficos interactivos
    tab_graf1, tab_graf2, tab_datos = st.tabs([
        "📊 Curva de Demanda 7 Días",
        "📅 Perfil por Día de Semana",
        "📑 Tabla de Detalle"
    ])

    with tab_graf1:
        # Demanda agregada por día proyectado
        daily_proj = (
            forecast_df.groupby(["fecha", "dia_semana_nombre", "es_fin_de_semana"], as_index=False)
            .agg({
                "demanda_base": "sum",
                "demanda_con_margen": "sum"
            })
            .sort_values(by="fecha")
        )
        daily_proj["fecha_label"] = daily_proj.apply(
            lambda r: f"{r['dia_semana_nombre']} ({r['fecha'].strftime('%d/%m')})", axis=1
        )

        fig1 = go.Figure()
        fig1.add_trace(go.Bar(
            x=daily_proj["fecha_label"],
            y=daily_proj["demanda_base"],
            name="Demanda Base (Promedio)",
            marker_color="#3B82F6"
        ))
        fig1.add_trace(go.Bar(
            x=daily_proj["fecha_label"],
            y=daily_proj["demanda_con_margen"] - daily_proj["demanda_base"],
            name=f"Margen Seguridad (+{margen_pct}%)",
            marker_color="#10B981"
        ))
        fig1.update_layout(
            barmode="stack",
            title="Proyección de Platos Totales por Día (Próxima Semana)",
            xaxis_title="Día",
            yaxis_title="Porciones / Platos Estimados",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig1, use_container_width=True)

    with tab_graf2:
        # Perfiles históricos por día de la semana
        dow_profiles = forecasting_engine.calculate_day_of_week_profiles(sales_df)
        if not dow_profiles.empty:
            fig2 = px.bar(
                dow_profiles,
                x="dia_semana_nombre",
                y="promedio_diario",
                color="plato",
                title="Consumo Promedio Histórico por Día de la Semana",
                labels={"dia_semana_nombre": "Día de la Semana", "promedio_diario": "Promedio Diario de Platos", "plato": "Plato"},
                category_orders={"dia_semana_nombre": list(DAYS_OF_WEEK_ES.values())}
            )
            st.plotly_chart(fig2, use_container_width=True)

    with tab_datos:
        st.dataframe(
            forecast_df[[
                "fecha", "dia_semana_nombre", "es_fin_de_semana", "plato",
                "demanda_base", "margen_seguridad_unidades", "demanda_con_margen"
            ]].rename(columns={
                "fecha": "Fecha",
                "dia_semana_nombre": "Día",
                "es_fin_de_semana": "Fin de Semana",
                "plato": "Plato",
                "demanda_base": "Demanda Base",
                "margen_seguridad_unidades": f"Margen (+{margen_pct}%)",
                "demanda_con_margen": "Demanda con Margen"
            }),
            use_container_width=True
        )
