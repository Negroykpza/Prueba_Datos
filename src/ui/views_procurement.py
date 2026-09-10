"""Vista 3: Dashboard Financiero EZtock, Métricas Primarias, Alertas Operativas y Compras por Proveedor."""

import urllib.parse
from datetime import timedelta
import streamlit as st
import pandas as pd
from src.services.forecasting import ForecastingEngine
from src.services.procurement import ProcurementService
from src.config import APP_NAME, APP_TAGLINE
from src.ui.components import render_financial_hero_card, render_info_banner


def render_procurement_dashboard_view(
    forecasting_engine: ForecastingEngine,
    procurement_service: ProcurementService
):
    st.markdown(f'<div class="main-header">💰 Dashboard Financiero & Compras ($ CLP) | {APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Gestión práctica de costos gastronómicos: métricas financieras clave, control de fugas de dinero y pedidos clasificados por proveedor.</div>',
        unsafe_allow_html=True
    )

    sales_df = st.session_state.get("sales_df")
    if sales_df is None or sales_df.empty:
        st.warning("⚠️ Para calcular la orden de compra y ver las métricas financieras, primero sube tu archivo CSV o presiona 'Usar Datos Demo' en la Pestaña 1.")
        return

    # 1. Controles Superiores: Horizonte, Margen y Restaurante
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1.2, 1.2, 1.2])

    with col_ctrl1:
        filtro_horizonte = st.radio(
            "📅 Período de Abastecimiento:",
            options=["🎯 Solo Fin de Semana (Vie - Sáb - Dom)", "🗓️ Próximos 7 Días Corridos"],
            index=0,
            help="En Chile, la mayor demanda de perecibles se concentra de viernes a domingo."
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
            help="Aparecerá en el encabezado de los pedidos de WhatsApp y reportes formales."
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

    # 3. Cálculo de la Lista de Compras y Métricas Financieras Primarias
    shopping_df = procurement_service.calculate_shopping_list(forecast_df, only_weekend=solo_fin_semana)

    if shopping_df.empty:
        st.error("No se pudieron generar compras. Asegúrate de tener escandallos e insumos guardados en la Pestaña 2.")
        return

    # Métricas Financieras Primarias
    fin_kpis = procurement_service.calculate_financial_kpis(shopping_df, forecast_df, is_weekend_only=solo_fin_semana)
    alerts = procurement_service.get_operational_alerts(shopping_df)
    legacy_metrics = procurement_service.calculate_waste_and_cost_metrics(shopping_df, is_weekend_only=solo_fin_semana)

    ahorro_mes_str = f"${int(fin_kpis['ahorro_mes_clp']):,}".replace(",", ".")
    puntos_fuga_str = f"${int(fin_kpis['puntos_fuga_clp']):,}".replace(",", ".")
    total_orden_str = f"${int(fin_kpis['total_orden_clp']):,}".replace(",", ".")
    ventas_est_str = f"${int(fin_kpis['ventas_proyectadas_clp']):,}".replace(",", ".")

    st.markdown("---")

    # =========================================================================
    # 1. TARJETAS KPI FINANCIERAS (SECCIÓN SUPERIOR)
    # =========================================================================
    st.subheader("💵 Métricas Financieras Primarias")

    c_kpi1, c_kpi2, c_kpi3 = st.columns(3)

    with c_kpi1:
        render_financial_hero_card(
            title="Ahorro Comprobado del Mes ($ CLP)",
            value=f"{ahorro_mes_str} CLP",
            caption="Diferencia real entre compras intuitivas sin control y compras optimizadas.",
            badge="🟢 +15% EFICIENCIA",
            theme="green"
        )

    with c_kpi2:
        render_financial_hero_card(
            title="Puntos de Fuga de Dinero ($ CLP)",
            value=f"{puntos_fuga_str} CLP",
            caption="Capital en insumos perecibles (<48h) en riesgo de merma si no se rota a tiempo.",
            badge="🔴 CAPITAL EN RIESGO",
            theme="red"
        )

    with c_kpi3:
        render_financial_hero_card(
            title="Food Cost Proyectado (%)",
            value=f"{fin_kpis['food_cost_pct']:.1f}%",
            caption=f"Inversión de {total_orden_str} CLP sobre ventas estimadas de {ventas_est_str} CLP.",
            badge="🎯 RANGO ÓPTIMO (28% - 32%)",
            theme="blue"
        )

    st.markdown("---")

    # =========================================================================
    # 2. SECCIÓN DE ALERTAS Y PUNTOS DE FUGA (TARJETAS DIRECTAS DE TEXTO)
    # =========================================================================
    st.subheader("⚡ Alertas Operativas y Puntos de Fuga")
    st.markdown(
        "<span style='font-size: 0.92rem; color: #64748B;'>Decisiones operativas inmediatas para cuidar el flujo de caja y evitar botar insumos perecibles a la basura.</span>",
        unsafe_allow_html=True
    )

    col_alert_frena, col_alert_promo = st.columns(2)

    # Tarjeta 1: 🔴 Frena Compras (Insumos con sobrestock suficiente)
    with col_alert_frena:
        frena_items_html = ""
        for item in alerts["frena_compras"]:
            frena_items_html += f"""
                <div style="margin-bottom: 12px; padding: 10px 12px; background: #FFFFFF; border: 1px solid #FECACA; border-radius: 6px;">
                    <div style="font-weight: 700; color: #991B1B; font-size: 0.92rem;">
                        🛑 {item['insumo']}
                    </div>
                    <div style="font-size: 0.84rem; color: #4B5563; margin-top: 3px; line-height: 1.4;">
                        {item['motivo']}
                    </div>
                    <div style="font-size: 0.78rem; font-weight: 600; color: #059669; margin-top: 4px;">
                        💰 Flujo de caja retenido: {item['ahorro_estimado']}
                    </div>
                </div>
            """

        st.markdown(f"""
            <div style="background-color: #FEF2F2; border: 2px solid #EF4444; border-radius: 10px; padding: 18px; box-shadow: 0 2px 5px rgba(0,0,0,0.04); min-height: 290px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                    <span style="font-size: 1.05rem; font-weight: 800; color: #991B1B;">
                        🔴 Frena Compras (Sobrestock en Bodega)
                    </span>
                    <span style="background: #FECACA; color: #7F1D1D; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">
                        PAUSAR PEDIDOS
                    </span>
                </div>
                <div style="font-size: 0.85rem; color: #7F1D1D; margin-bottom: 12px;">
                    Insumos con cobertura garantizada en bodega. <strong>Evita compras impulsivas</strong> que inmovilicen dinero:
                </div>
                {frena_items_html}
            </div>
        """, unsafe_allow_html=True)

    # Tarjeta 2: 🟡 Promoción Preventiva (Insumos cerca de vencer con sugerencia de menú del día)
    with col_alert_promo:
        promo_items_html = ""
        for item in alerts["promociones"]:
            promo_items_html += f"""
                <div style="margin-bottom: 12px; padding: 10px 12px; background: #FFFFFF; border: 1px solid #FDE68A; border-radius: 6px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: #92400E; font-size: 0.92rem;">
                            🍽️ {item['insumo']}
                        </span>
                        <span style="font-size: 0.75rem; color: #B45309; font-weight: 600;">
                            ⏳ {item['caducidad']}
                        </span>
                    </div>
                    <div style="font-size: 0.84rem; font-weight: 600; color: #1E293B; margin-top: 4px;">
                        📌 {item['plato_sugerido']}
                    </div>
                    <div style="font-size: 0.80rem; color: #4B5563; margin-top: 2px; line-height: 1.35;">
                        💡 {item['estrategia']}
                    </div>
                </div>
            """

        st.markdown(f"""
            <div style="background-color: #FFFBEB; border: 2px solid #F59E0B; border-radius: 10px; padding: 18px; box-shadow: 0 2px 5px rgba(0,0,0,0.04); min-height: 290px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                    <span style="font-size: 1.05rem; font-weight: 800; color: #92400E;">
                        🟡 Promoción Preventiva (Menú del Día)
                    </span>
                    <span style="background: #FDE68A; color: #78350F; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">
                        VENTA ACELERADA
                    </span>
                </div>
                <div style="font-size: 0.85rem; color: #78350F; margin-bottom: 12px;">
                    Insumos perecibles críticos (&lt; 48h). <strong>Saca estos platos a la carta hoy</strong> para asegurar su rotación:
                </div>
                {promo_items_html}
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # =========================================================================
    # 3. MÓDULO DE LISTA DE COMPRAS LIMPIA (AGRUPADA POR PROVEEDOR)
    # =========================================================================
    st.subheader("🛒 Lista de Compras Agrupada por Proveedor")
    st.markdown(
        "<span style='font-size: 0.92rem; color: #64748B;'>Cada proveedor recibe únicamente los insumos que le corresponden con su total independiente, listo para enviar por WhatsApp.</span>",
        unsafe_allow_html=True
    )

    # Identificar proveedores únicos en la orden
    proveedores_unicos = sorted(shopping_df["proveedor"].unique())

    for idx, prov in enumerate(proveedores_unicos):
        prov_df = shopping_df[shopping_df["proveedor"] == prov].copy()
        prov_subtotal = int(prov_df["subtotal_cost_clp"].sum())
        prov_subtotal_str = f"${prov_subtotal:,}".replace(",", ".")
        prov_slug = prov.split()[0].replace("🐟", "pesca").replace("🥩", "carne").replace("🥬", "vega").replace("🧀", "lacteo").replace("🏪", "gral")

        with st.container():
            st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px 18px; margin-top: 14px; margin-bottom: 8px;">
                    <div>
                        <span style="font-size: 1.15rem; font-weight: 700; color: #0F172A;">{prov}</span>
                        <span style="font-size: 0.85rem; color: #64748B; margin-left: 10px;">({len(prov_df)} insumos)</span>
                    </div>
                    <div style="font-size: 1.1rem; font-weight: 800; color: #047857;">
                        Subtotal: {prov_subtotal_str} CLP
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Tabla limpia para este proveedor
            display_prov_df = prov_df.copy().rename(columns={
                "insumo": "Insumo Perecible",
                "total_sugerido": "Cantidad Requerida",
                "unidad": "Unidad",
                "cost_per_unit": "Precio Unitario ($ CLP)",
                "subtotal_cost_clp": "Subtotal ($ CLP)",
                "riesgo_caducidad": "Caducidad",
                "platos_asociados": "Platos que lo Consumen"
            })

            st.dataframe(
                display_prov_df[[
                    "Insumo Perecible", "Cantidad Requerida", "Unidad",
                    "Precio Unitario ($ CLP)", "Subtotal ($ CLP)",
                    "Caducidad", "Platos que lo Consumen"
                ]].style.format({
                    "Cantidad Requerida": "{:.2f}",
                    "Precio Unitario ($ CLP)": "${:,.0f} CLP",
                    "Subtotal ($ CLP)": "${:,.0f} CLP"
                }),
                use_container_width=True
            )

            # Generar texto independiente de WhatsApp para este proveedor
            wa_text_prov = procurement_service.format_supplier_whatsapp_message(
                supplier_name=prov,
                supplier_df=prov_df,
                restaurant_name=restaurant_name,
                periodo_label=periodo_label
            )

            col_btn1, col_btn2 = st.columns([1.5, 2.5])

            with col_btn1:
                # Botón de copiar pedido de WhatsApp independiente
                btn_key = f"btn_wa_copy_{idx}_{prov_slug}"
                if st.button(f"📋 Copiar pedido para WhatsApp", key=btn_key, use_container_width=True):
                    st.session_state[f"show_wa_{idx}"] = True
                    st.toast(f"✅ ¡Pedido para {prov} listo para copiar!")

            with col_btn2:
                # Enlace directo a WhatsApp Web
                encoded_msg = urllib.parse.quote(wa_text_prov)
                wa_url = f"https://wa.me/?text={encoded_msg}"
                st.link_button(f"📲 Abrir en WhatsApp Web ({prov.split('(')[0].strip()})", wa_url, use_container_width=True)

            # Mostrar bloque de texto para copiar si fue accionado o bajo expander
            with st.expander(f"👁️ Ver mensaje formateado para {prov}", expanded=st.session_state.get(f"show_wa_{idx}", False)):
                st.code(wa_text_prov, language="text")

        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    st.markdown("---")

    # =========================================================================
    # 4. EXPORTACIONES FORMALES (PDF Y EXCEL CONSOLIDADOS)
    # =========================================================================
    st.subheader(f"📄 Descargar Documentos Formales ({APP_NAME})")
    col_doc1, col_doc2 = st.columns(2)

    with col_doc1:
        try:
            pdf_bytes = procurement_service.generate_pdf_report(
                shopping_df,
                restaurant_name=restaurant_name,
                periodo_label=periodo_label,
                safety_margin_pct=margen_pct,
                metrics=legacy_metrics
            )
            st.download_button(
                label=f"📄 Descargar Orden Consolidada en PDF ({APP_NAME})",
                data=pdf_bytes,
                file_name=f"eztock_orden_{restaurant_name.replace(' ', '_')}_{'findesemana' if solo_fin_semana else '7dias'}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error al generar PDF: {e}")

    with col_doc2:
        excel_bytes = procurement_service.export_to_excel_bytes(shopping_df, periodo_label)
        st.download_button(
            label=f"📊 Descargar Planilla Excel Completa ({APP_NAME})",
            data=excel_bytes,
            file_name=f"eztock_pedido_{'findesemana' if solo_fin_semana else '7dias'}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
