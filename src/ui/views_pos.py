"""Vista 1: Carga, Normalización y Diagnóstico de Ventas POS para EZtock."""

import time
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.config import APP_NAME, DAYS_OF_WEEK_ES
from src.services.pos_parser import POSParser
from src.services.recipe_service import RecipeService
from src.ui.components import render_info_banner, render_metric_card


def render_pos_view(pos_parser: POSParser, recipe_service: RecipeService):
    st.markdown(f'<div class="main-header">📂 Ingesta & Normalización de Ventas POS | {APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Carga cualquier reporte de ventas (Fudo, Restobar, Totem, Excel exportado). Detectamos automáticamente columnas y platos de tu carta.</div>',
        unsafe_allow_html=True
    )

    render_info_banner(
        "💡 Flexibilidad Total de Archivos",
        "No requieres cambiar los nombres de tus columnas. Nuestro motor inteligente detecta automáticamente fecha, nombre de plato y cantidad vendida."
    )

    col_up1, col_up2 = st.columns([2, 1])

    with col_up1:
        uploaded_file = st.file_uploader(
            "Arrastra o selecciona el archivo CSV de ventas de tu restaurante:",
            type=["csv"],
            help="Soporta exportaciones de cualquier POS gastronómico común en Chile."
        )

    with col_up2:
        st.write("**¿No tienes un archivo a mano?**")
        if st.button("🚀 Usar Datos Demo de 90 Días", type="secondary", use_container_width=True):
            with st.status("🚀 Procesando datos de demostración...", expanded=True) as status:
                st.write("Generando 90 días de historial gastronómico chileno...")
                time.sleep(0.3)
                st.write("Analizando patrones de demanda por día de la semana...")
                time.sleep(0.3)
                df_demo = pos_parser.load_demo_data()
                st.session_state["sales_df"] = df_demo
                st.session_state["pos_summary"] = pos_parser.get_summary(df_demo)
                detected = pos_parser.extract_unique_dishes(df_demo)
                st.session_state["detected_dishes"] = detected
                recipe_service.sync_with_detected_dishes(detected)
                st.write("Sincronizando platos detectados con la carta...")
                status.update(label="✅ ¡Datos de demo cargados y normalizados con éxito!", state="complete", expanded=False)
            st.toast(f"✅ ¡{len(detected)} platos detectados en los datos de demostración!")

    # Procesar archivo subido por el usuario con animación de progreso
    if uploaded_file is not None:
        try:
            with st.status("⚡ Procesando archivo CSV en EZtock...", expanded=True) as status:
                st.write("Detectando codificación de caracteres y delimitadores...")
                time.sleep(0.2)
                st.write("Mapeando columnas de Fecha, Plato y Cantidad vendida...")
                df_parsed = pos_parser.parse_csv(uploaded_file)
                time.sleep(0.2)
                st.write("Validando y normalizando formatos de fecha...")
                st.session_state["sales_df"] = df_parsed
                st.session_state["pos_summary"] = pos_parser.get_summary(df_parsed)
                detected = pos_parser.extract_unique_dishes(df_parsed)
                st.session_state["detected_dishes"] = detected
                recipe_service.sync_with_detected_dishes(detected)
                st.write(f"Identificando {len(detected)} platos únicos de la carta...")
                status.update(label="✅ ¡Archivo normalizado y procesado exitosamente!", state="complete", expanded=False)

            st.toast(f"✅ Se normalizaron {len(df_parsed):,} registros exitosamente.")
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo CSV: {str(e)}")
            st.info("Asegúrate de que el CSV contenga al menos una columna de fecha, una de plato y una de cantidad.")

    # Mostrar diagnóstico y analítica si hay datos cargados
    if st.session_state.get("sales_df") is not None:
        df = st.session_state["sales_df"]
        summary = st.session_state["pos_summary"]

        st.markdown("---")
        st.subheader("📊 Diagnóstico Inmediato de Ventas")

        # 4 Tarjetas de Métricas KPI en Dark Mode Nativo con Variaciones (Deltas)
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

        total_unidades = summary.get("total_unidades", int(df["cantidad"].sum()))
        total_platos = summary.get("total_platos", df["plato"].nunique())
        dias_totales = summary.get("dias_totales", df["fecha"].nunique())
        pct_fin_semana = summary.get("pct_fin_semana", 0.0)
        rango_str = summary.get("rango_fechas", "N/A")

        with kpi_col1:
            render_metric_card(
                title="Total Platos Vendidos",
                value=f"{total_unidades:,}".replace(",", "."),
                delta="100% Procesado",
                delta_type="positive",
                caption="Registros POS limpios"
            )

        with kpi_col2:
            render_metric_card(
                title="Platos Únicos en Carta",
                value=str(total_platos),
                delta="Detección Auto",
                delta_type="neutral",
                caption="Platos con demanda activa"
            )

        with kpi_col3:
            promedio_diario = int(total_unidades / dias_totales) if dias_totales > 0 else 0
            render_metric_card(
                title="Días de Histórico",
                value=str(dias_totales),
                delta=f"~{promedio_diario} un/día",
                delta_type="positive",
                caption="Período analizado"
            )

        with kpi_col4:
            render_metric_card(
                title="Peak Fin de Semana",
                value=f"{pct_fin_semana:.1f}%",
                delta="Vie - Sáb - Dom",
                delta_type="warning",
                caption=f"Rango: {rango_str}"
            )

        st.markdown("---")

        # Visualización de Datos Avanzada: Gráficos Interactivos de Diagnóstico (Plotly)
        st.subheader("📈 Análisis y Tendencia de Ventas")

        tab_graf1, tab_graf2 = st.tabs(["📉 Tendencia Temporal Diaria", "📅 Estacionalidad Semanal"])

        with tab_graf1:
            daily_sales = (
                df.groupby("fecha", as_index=False)["cantidad"]
                .sum()
                .sort_values(by="fecha")
            )
            daily_sales["fecha_dt"] = pd.to_datetime(daily_sales["fecha"])
            daily_sales["media_movil_7d"] = daily_sales["cantidad"].rolling(window=7, min_periods=1).mean()
            daily_sales["dia_semana"] = daily_sales["fecha_dt"].dt.dayofweek.map(DAYS_OF_WEEK_ES)

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=daily_sales["fecha_dt"],
                y=daily_sales["cantidad"],
                mode="lines+markers",
                name="Ventas Diarias",
                line=dict(color="#38BDF8", width=2),
                marker=dict(size=5, color="#0284C7"),
                fill="tozeroy",
                fillcolor="rgba(56, 189, 248, 0.08)",
                hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Platos Vendidos: <b>%{y} un</b><extra></extra>"
            ))
            fig_trend.add_trace(go.Scatter(
                x=daily_sales["fecha_dt"],
                y=daily_sales["media_movil_7d"],
                mode="lines",
                name="Tendencia (Promedio 7D)",
                line=dict(color="#34D399", width=2.5, dash="dot"),
                hovertemplate="Media Móvil 7D: <b>%{y:.1f} un</b><extra></extra>"
            ))

            fig_trend.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#CBD5E1"),
                title="Curva de Demanda Temporal Diaria y Tendencia de Fondo",
                xaxis=dict(
                    title="Fecha",
                    gridcolor="#334155",
                    tickformat="%d/%m"
                ),
                yaxis=dict(
                    title="Platos Vendidos",
                    gridcolor="#334155"
                ),
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        with tab_graf2:
            dow_sales = (
                df.groupby(["dia_semana_num", "dia_semana_nombre"], as_index=False)["cantidad"]
                .mean()
                .sort_values(by="dia_semana_num")
            )
            dow_sales["color_bar"] = dow_sales["dia_semana_num"].apply(
                lambda x: "#34D399" if x in [4, 5, 6] else "#38BDF8"
            )

            fig_dow = go.Figure()
            fig_dow.add_trace(go.Bar(
                x=dow_sales["dia_semana_nombre"],
                y=dow_sales["cantidad"],
                marker_color=dow_sales["color_bar"],
                hovertemplate="<b>%{x}</b><br>Promedio: <b>%{y:.1f} un/día</b><extra></extra>",
                text=dow_sales["cantidad"].round(1),
                textposition="auto"
            ))

            fig_dow.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#CBD5E1"),
                title="Promedio de Venta por Día de la Semana (Destacado Fin de Semana en Verde)",
                xaxis=dict(gridcolor="#334155", categoryorder="array", categoryarray=list(DAYS_OF_WEEK_ES.values())),
                yaxis=dict(title="Promedio Unidades", gridcolor="#334155")
            )
            st.plotly_chart(fig_dow, use_container_width=True)

        st.markdown("---")

        # Escalabilidad en "Platos Detectados": Tabla Compacta con Métricas
        st.subheader("🍽️ Desglose de Platos Detectados en tu Carta")
        st.markdown("<span style='font-size: 0.88rem; color: #94A3B8;'>Lista escalable para cartas extensas (50+ platos) con métricas de participación en ventas:</span>", unsafe_allow_html=True)

        dish_stats = (
            df.groupby("plato", as_index=False)
            .agg(
                total_vendido=("cantidad", "sum"),
                dias_con_venta=("fecha", "nunique")
            )
            .sort_values(by="total_vendido", ascending=False)
            .reset_index(drop=True)
        )
        dish_stats["promedio_diario"] = (dish_stats["total_vendido"] / dias_totales).round(1)
        dish_stats["participacion_pct"] = (dish_stats["total_vendido"] / total_unidades * 100).round(1)

        col_cfg_dishes = {
            "plato": st.column_config.TextColumn("Plato de la Carta", width="medium"),
            "total_vendido": st.column_config.NumberColumn("Total Vendido", format="%d un", width="small"),
            "promedio_diario": st.column_config.NumberColumn("Promedio Diario", format="%.1f un", width="small"),
            "dias_con_venta": st.column_config.NumberColumn("Días Activo", format="%d días", width="small"),
            "participacion_pct": st.column_config.ProgressColumn(
                "Participación en Ventas",
                format="%.1f%%",
                min_value=0.0,
                max_value=float(dish_stats["participacion_pct"].max() if not dish_stats.empty else 100.0),
                width="medium"
            )
        }

        st.dataframe(
            dish_stats,
            column_config=col_cfg_dishes,
            use_container_width=True,
            hide_index=True,
            height=260
        )

        st.markdown("---")

        # Inspección de Registros Normalizados con Mayor Jerarquía Visual
        st.markdown("""
            <div class="data-inspect-card">
                <div class="data-inspect-header">
                    <span style="font-weight: 700; font-size: 1rem; color: #F1F5F9;">🔍 Explorador de Registros Normalizados</span>
                    <span class="delta-pill delta-positive">Datos Limpios y Validados</span>
                </div>
                <span style="font-size: 0.85rem; color: #94A3B8;">
                    Inspecciona las transacciones normalizadas por EZtock o descarga el archivo estandarizado para tus reportes.
                </span>
            </div>
        """, unsafe_allow_html=True)

        with st.expander("📂 Abrir Tabla Completa de Registros Normalizados (Primeras 100 filas)", expanded=False):
            st.dataframe(df.head(100), use_container_width=True, hide_index=True)
            csv_export = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Descargar Datos Normalizados en CSV",
                data=csv_export,
                file_name="ventas_normalizadas_eztock.csv",
                mime="text/csv",
                use_container_width=True
            )

        # Botón de Llamado a la Acción (CTA) destacado para guiar el flujo hacia Pestaña 2
        st.markdown('<div class="cta-container">', unsafe_allow_html=True)
        col_spacer, col_cta = st.columns([1.5, 1])
        with col_cta:
            if st.button("Continuar al Editor de Escandallos ($ CLP) ➡️", type="primary", use_container_width=True):
                st.session_state["selected_tab_name"] = "🥗 2. Editor de Escandallos ($ CLP)"
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.info("👆 Sube tu archivo CSV de ventas o presiona 'Usar Datos Demo' para iniciar el diagnóstico inteligente en EZtock.")
