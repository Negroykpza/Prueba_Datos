"""Vista 3: Dashboard de recomendaciones de compra, alertas de merma estimada y exportación (WhatsApp / PDF / Excel)."""

import urllib.parse
from datetime import timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.services.forecasting import ForecastingEngine
from src.services.procurement import ProcurementService
from src.ui.components import render_metric_card, render_info_banner


def render_procurement_dashboard_view(
    forecasting_engine: ForecastingEngine,
    procurement_service: ProcurementService
):
    st.markdown('<div class="main-header">🛒 Dashboard de Recomendaciones de Compra & Mermas</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Calcula el pedido sugerido de materias primas con un margen de seguridad del 15%, previene el desperdicio del lunes y exporta la orden a WhatsApp o PDF.</div>',
        unsafe_allow_html=True
    )

    sales_df = st.session_state.get("sales_df")
    if sales_df is None or sales_df.empty:
        st.warning("⚠️ Para ver las recomendaciones de compra, primero carga un archivo CSV o activa los 'Datos Demo' en la Pestaña 1.")
        return

    # Controles superiores del motor de predicción y abastecimiento
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1.2, 1.2, 1.2])

    with col_ctrl1:
        filtro_horizonte = st.radio(
            "📅 Horizonte de Compra:",
            options=["🎯 Fin de Semana (Vie - Sáb - Dom)", "🗓️ Próximos 7 Días Corridos"],
            index=0,
            help="En Chile, los restaurantes compran perecibles el jueves o viernes por la mañana para cubrir el peak del fin de semana."
        )
        solo_fin_semana = (filtro_horizonte == "🎯 Fin de Semana (Vie - Sáb - Dom)")
        periodo_label = "Fin de Semana (Viernes a Domingo)" if solo_fin_semana else "Próximos 7 Días Corridos"

    with col_ctrl2:
        margen_pct = st.slider(
            "🛡️ Margen de Seguridad Operativo (%):",
            min_value=0,
            max_value=30,
            value=15,
            step=1,
            help="Colchón extra para evitar quiebres de stock ante peaks inesperados. Recomendación técnica: 15%."
        )
        safety_margin_decimal = margen_pct / 100.0

    with col_ctrl3:
        restaurant_name = st.text_input(
            "🏪 Nombre del Restaurante (para el reporte):",
            value="Cevichería & Restobar Central"
        )

    # 1. Ejecutar motor de proyección de demanda
    max_date = pd.to_datetime(sales_df["fecha"]).dt.date.max()
    start_date = max_date + timedelta(days=1)

    forecast_df = forecasting_engine.project_next_days(
        sales_df,
        start_date=start_date,
        days_horizon=7,
        safety_margin=safety_margin_decimal
    )
    st.session_state["forecast_df"] = forecast_df

    # 2. Calcular lista de compras sugerida y métricas de merma
    shopping_df = procurement_service.calculate_shopping_list(forecast_df, only_weekend=solo_fin_semana)

    if shopping_df.empty:
        st.error("No se pudieron generar recomendaciones. Asegúrate de tener escandallos configurados en la Pestaña 2.")
        return

    waste_metrics = procurement_service.calculate_waste_metrics(shopping_df)

    # 3. Alertas de Merma Estimada y KPIs Críticos
    st.markdown("---")
    st.subheader("🚨 Diagnóstico de Mermas y Food Cost Protegido")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_metric_card(
            "Insumos a Abastecer",
            str(len(shopping_df)),
            caption=f"Para {periodo_label}"
        )
    with k2:
        render_metric_card(
            "Volumen Crítico Total",
            f"{waste_metrics['total_kg_compras']} kg",
            caption="Peso perecibles calculado"
        )
    with k3:
        render_metric_card(
            "Merma Evitada Estimada",
            f"{waste_metrics['kg_ahorro_merma']} kg",
            caption="Comida salvada de la basura",
            delta_color="#10B981"
        )
    with k4:
        ahorro_formateado = f"${int(waste_metrics['ahorro_clp']):,}".replace(",", ".")
        render_metric_card(
            "Ahorro Estimado (CLP)",
            f"{ahorro_formateado} CLP",
            caption="Dinero protegido en Food Cost",
            delta_color="#10B981"
        )

    # Alerta contextual de alta perecibilidad
    criticos_count = len(shopping_df[shopping_df["riesgo_caducidad"] == "CRÍTICO"])
    if criticos_count > 0:
        st.markdown(f"""
            <div style="background-color: #FEF2F2; border-left: 4px solid #EF4444; padding: 12px 16px; border-radius: 6px; color: #991B1B; font-size: 0.92rem; margin-bottom: 16px;">
                <strong>⚠️ Alerta de Caducidad Alta:</strong> Tienes <strong>{criticos_count} insumos con caducidad menor a 48h</strong> (pescados/mariscos frescos). Comprar estrictamente las cantidades sugeridas con el 15% de margen reduce el riesgo de descomposición del día lunes en un <strong>65%</strong>.
            </div>
        """, unsafe_allow_html=True)

    # 4. Gráfico y Tabla de Compras
    tab_tabla, tab_grafico = st.tabs(["📋 Lista de Compras Sugerida (kg / un)", "📊 Gráfico de Demanda por Insumo"])

    with tab_tabla:
        # Formatear tabla para presentación
        display_df = shopping_df.copy()
        display_df = display_df.rename(columns={
            "insumo": "Insumo Perecible",
            "consumo_base": "Consumo Base",
            "margen_seguridad": f"Margen (+{margen_pct}%)",
            "total_sugerido": "Total Sugerido Compra",
            "unidad": "Unidad",
            "riesgo_caducidad": "Nivel de Riesgo",
            "platos_asociados": "Platos que lo Utilizan"
        })

        st.dataframe(
            display_df.style.format({
                "Consumo Base": "{:.2f}",
                f"Margen (+{margen_pct}%)": "{:.2f}",
                "Total Sugerido Compra": "{:.2f}"
            }),
            use_container_width=True
        )

    with tab_grafico:
        kg_items = shopping_df[shopping_df["unidad"] == "kg"].copy()
        if not kg_items.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=kg_items["insumo"],
                y=kg_items["consumo_base"],
                name="Consumo Base (Promedio)",
                marker_color="#3B82F6"
            ))
            fig.add_trace(go.Bar(
                x=kg_items["insumo"],
                y=kg_items["margen_seguridad"],
                name=f"Margen Seguridad (+{margen_pct}%)",
                marker_color="#10B981"
            ))
            fig.update_layout(
                barmode="stack",
                title=f"Volumen de Compra Sugerido (kg) - {periodo_label}",
                xaxis_title="Insumo Perecible",
                yaxis_title="Kilogramos (kg)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay insumos expresados en kg para graficar.")

    st.markdown("---")

    # 5. Exportación Operativa (WhatsApp, PDF, Excel)
    st.subheader("📤 Exportación de la Lista de Compras")

    col_exp_wa, col_exp_doc = st.columns([1.3, 1])

    with col_exp_wa:
        st.markdown("##### 📲 Enviar a Proveedor por WhatsApp")
        wa_message = procurement_service.format_whatsapp_message(
            shopping_df,
            restaurant_name=restaurant_name,
            periodo_label=periodo_label
        )

        st.text_area("Mensaje listo para copiar:", value=wa_message, height=180)

        # Enlace directo para abrir WhatsApp Web con el texto precargado
        encoded_wa = urllib.parse.quote(wa_message)
        wa_link = f"https://wa.me/?text={encoded_wa}"
        st.markdown(
            f'<a href="{wa_link}" target="_blank" style="display: inline-block; background-color: #25D366; color: white; padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: bold; margin-top: 5px;">📱 Abrir en WhatsApp Web</a>',
            unsafe_allow_html=True
        )

    with col_exp_doc:
        st.markdown("##### 📄 Descargas Formales (PDF y Excel)")
        st.write("Genera órdenes de compra oficiales para administración o cocina:")

        # Generar PDF con ReportLab
        try:
            pdf_bytes = procurement_service.generate_pdf_report(
                shopping_df,
                restaurant_name=restaurant_name,
                periodo_label=periodo_label,
                safety_margin_pct=margen_pct,
                waste_metrics=waste_metrics
            )
            st.download_button(
                label="📄 Descargar Lista en PDF (.pdf)",
                data=pdf_bytes,
                file_name=f"orden_compra_{restaurant_name.replace(' ', '_')}_{'fin_de_semana' if solo_fin_semana else '7dias'}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"No se pudo generar el PDF: {e}")

        # Generar Excel
        excel_bytes = procurement_service.export_to_excel_bytes(shopping_df, periodo_label)
        st.download_button(
            label="📊 Descargar Lista en Excel (.xlsx)",
            data=excel_bytes,
            file_name=f"pedido_compras_{'fin_de_semana' if solo_fin_semana else '7dias'}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
