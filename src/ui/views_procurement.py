"""Vista 3: Dashboard EZtock de recomendaciones de compra, costeo en CLP, alertas de merma y exportaciones."""

import urllib.parse
from datetime import timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.services.forecasting import ForecastingEngine
from src.services.procurement import ProcurementService
from src.config import APP_NAME, APP_TAGLINE
from src.ui.components import render_metric_card, render_info_banner


def render_procurement_dashboard_view(
    forecasting_engine: ForecastingEngine,
    procurement_service: ProcurementService
):
    st.markdown(f'<div class="main-header">🛒 Dashboard de Compras & Costos ($ CLP) | {APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-header">{APP_TAGLINE}. Calcula la demanda exacta con margen de seguridad, valoriza el pedido en pesos chilenos y calcula el ahorro por merma evitada.</div>',
        unsafe_allow_html=True
    )

    sales_df = st.session_state.get("sales_df")
    if sales_df is None or sales_df.empty:
        st.warning("⚠️ Para calcular la orden de compra, primero sube tu CSV o presiona 'Usar Datos Demo' en la Pestaña 1.")
        return

    # 1. Controles Superiores: Horizonte, Margen y Restaurante
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1.2, 1.2, 1.2])

    with col_ctrl1:
        filtro_horizonte = st.radio(
            "📅 Período de Abastecimiento:",
            options=["🎯 Solo Fin de Semana (Vie - Sáb - Dom)", "🗓️ Próximos 7 Días Corridos"],
            index=0,
            help="En Chile, los pedidos de perecibles se concentran para abastecer el peak de viernes a domingo."
        )
        solo_fin_semana = (filtro_horizonte == "🎯 Solo Fin de Semana (Vie - Sáb - Dom)")
        periodo_label = "Fin de Semana (Viernes a Domingo)" if solo_fin_semana else "Próximos 7 Días Corridos"

    with col_ctrl2:
        margen_pct = st.slider(
            "🛡️ Margen de Seguridad (%):",
            min_value=5,
            max_value=25,
            value=15,
            step=1,
            help="Colchón operativo para evitar quiebres de stock. Rango estándar recomendado: 10% a 15%."
        )
        safety_margin_decimal = margen_pct / 100.0

    with col_ctrl3:
        restaurant_name = st.text_input(
            "🏪 Nombre de tu Restaurante:",
            value="Restaurante & Bar Central",
            help="Aparecerá en el encabezado del PDF, Excel y WhatsApp"
        )

    # 2. Motor de Demanda y Proyección
    max_date = pd.to_datetime(sales_df["fecha"]).dt.date.max()
    start_date = max_date + timedelta(days=1)

    forecast_df = forecasting_engine.project_next_days(
        sales_df,
        start_date=start_date,
        days_horizon=7,
        safety_margin=safety_margin_decimal
    )
    st.session_state["forecast_df"] = forecast_df

    # 3. Cálculo de la Lista de Compras y Métricas de Costos en CLP
    shopping_df = procurement_service.calculate_shopping_list(forecast_df, only_weekend=solo_fin_semana)

    if shopping_df.empty:
        st.error("No se pudieron generar compras. Asegúrate de tener escandallos e insumos guardados en la Pestaña 2.")
        return

    metrics = procurement_service.calculate_waste_and_cost_metrics(shopping_df, is_weekend_only=solo_fin_semana)

    # 4. Tarjetas de KPIs Principales con Foco en CLP y Ahorro Mensual
    st.markdown("---")
    st.subheader("💰 Resumen Financiero y Ahorro en Mermas")

    k1, k2, k3, k4 = st.columns(4)

    total_orden_str = f"${int(metrics['total_orden_clp']):,}".replace(",", ".")
    ahorro_mensual_str = f"${int(metrics['ahorro_mensual_clp']):,}".replace(",", ".")

    with k1:
        render_metric_card(
            "Total Insumos (Kilos)",
            f"{metrics['total_kg_compras']} kg",
            caption="Peso perecibles a comprar",
            delta_color="#3B82F6"
        )
    with k2:
        render_metric_card(
            "Costo Total de la Orden",
            f"{total_orden_str} CLP",
            caption=f"Inversión para {periodo_label}",
            delta_color="#0F172A"
        )
    with k3:
        render_metric_card(
            "Ahorro Estimado Mensual",
            f"{ahorro_mensual_str} CLP",
            caption="Frente a la compra intuitiva",
            delta_color="#10B981"
        )
    with k4:
        render_metric_card(
            "Comida Salvada al Mes",
            f"~{metrics['kg_ahorro_merma'] * 4.3:.0f} kg",
            caption="Menos merma en basureros",
            delta_color="#10B981"
        )

    # Alerta contextual de riesgo de caducidad
    criticos_df = shopping_df[shopping_df["riesgo_caducidad"] == "CRÍTICO"]
    if not criticos_df.empty:
        criticos_list = ", ".join(criticos_df["insumo"].unique())
        st.markdown(f"""
            <div style="background-color: #FEF2F2; border-left: 4px solid #EF4444; padding: 12px 16px; border-radius: 6px; color: #991B1B; font-size: 0.92rem; margin-top: 12px; margin-bottom: 16px;">
                <strong>⚠️ Alerta de Insumos Críticos (&lt; 48h de vida útil):</strong> {criticos_list}.<br>
                Comprar estrictamente el volumen proyectado por {APP_NAME} evita el sobrestock que se descompone durante el día lunes.
            </div>
        """, unsafe_allow_html=True)

    # 5. Tabla Detallada de Compras y Costeo en CLP
    tab_tabla, tab_grafico = st.tabs(["📋 Detalle de la Orden ($ CLP)", "📊 Gráfico de Inversión por Insumo"])

    with tab_tabla:
        display_df = shopping_df.copy()
        display_df = display_df.rename(columns={
            "insumo": "Insumo Perecible",
            "total_sugerido": "Total a Comprar",
            "unidad": "Unidad",
            "cost_per_unit": "Precio Compra ($ CLP)",
            "subtotal_cost_clp": "Subtotal ($ CLP)",
            "riesgo_caducidad": "Caducidad",
            "platos_asociados": "Platos que lo Consumen"
        })

        st.dataframe(
            display_df[[
                "Insumo Perecible", "Total a Comprar", "Unidad",
                "Precio Compra ($ CLP)", "Subtotal ($ CLP)",
                "Caducidad", "Platos que lo Consumen"
            ]].style.format({
                "Total a Comprar": "{:.2f}",
                "Precio Compra ($ CLP)": "${:,.0f} CLP",
                "Subtotal ($ CLP)": "${:,.0f} CLP"
            }),
            use_container_width=True
        )

    with tab_grafico:
        fig = px.bar(
            shopping_df,
            x="insumo",
            y="subtotal_cost_clp",
            color="unidad",
            title=f"Inversión Estimada por Insumo ($ CLP) - {periodo_label}",
            labels={"insumo": "Insumo Perecible", "subtotal_cost_clp": "Subtotal ($ CLP)", "unidad": "Unidad"},
            text_auto=",.0f"
        )
        fig.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # 6. Exportaciones Operativas (WhatsApp, PDF, Excel) bajo la marca EZtock
    st.subheader(f"📤 Exportar Orden de Compra | {APP_NAME}")

    col_exp_wa, col_exp_doc = st.columns([1.3, 1])

    with col_exp_wa:
        st.markdown("##### 📲 Enviar por WhatsApp a Proveedor")
        wa_message = procurement_service.format_whatsapp_message(
            shopping_df,
            restaurant_name=restaurant_name,
            periodo_label=periodo_label,
            metrics=metrics
        )

        st.text_area("Mensaje formateado listo para enviar:", value=wa_message, height=190)

        encoded_wa = urllib.parse.quote(wa_message)
        wa_link = f"https://wa.me/?text={encoded_wa}"
        st.markdown(
            f'<a href="{wa_link}" target="_blank" style="display: inline-block; background-color: #25D366; color: white; padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: bold; margin-top: 5px;">📱 Abrir en WhatsApp Web con Pedido</a>',
            unsafe_allow_html=True
        )

    with col_exp_doc:
        st.markdown(f"##### 📄 Documentos Formales ({APP_NAME})")
        st.write("Genera reportes valorizados con precios en $ CLP:")

        # Generar PDF formal con ReportLab
        try:
            pdf_bytes = procurement_service.generate_pdf_report(
                shopping_df,
                restaurant_name=restaurant_name,
                periodo_label=periodo_label,
                safety_margin_pct=margen_pct,
                metrics=metrics
            )
            st.download_button(
                label=f"📄 Descargar Orden en PDF ({APP_NAME})",
                data=pdf_bytes,
                file_name=f"eztock_orden_{restaurant_name.replace(' ', '_')}_{'findesemana' if solo_fin_semana else '7dias'}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error al generar PDF: {e}")

        # Generar Excel
        excel_bytes = procurement_service.export_to_excel_bytes(shopping_df, periodo_label)
        st.download_button(
            label=f"📊 Descargar Planilla Excel ({APP_NAME})",
            data=excel_bytes,
            file_name=f"eztock_pedido_{'findesemana' if solo_fin_semana else '7dias'}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
