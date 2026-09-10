"""Punto de entrada principal de la plataforma SaaS EZtock.

Gestión inteligente de stock, compras y costos gastronómicos en Chile:
- Pestaña 1: Carga de archivo CSV (o botón para usar los datos demo generados).
- Pestaña 2: Editor interactivo de escandallos e insumos con costeo en pesos chilenos ($ CLP).
- Pestaña 3: Dashboard Financiero Primario: Tarjetas de Ahorro en $ CLP, Puntos de Fuga y Food Cost Proyectado (%).
- Pestaña 4: Mis Proveedores: Lista de compras agrupada por proveedor con botón de WhatsApp independiente.
"""

import urllib.parse
from datetime import timedelta
import streamlit as st
import pandas as pd
from src.config import APP_NAME, APP_TAGLINE, APP_VERSION
from src.services.pos_parser import POSParser
from src.services.recipe_service import RecipeService
from src.services.forecasting import ForecastingEngine
from src.services.procurement import ProcurementService
from src.ui.components import inject_custom_styles, render_financial_hero_card, render_info_banner
from src.ui.views_pos import render_pos_view
from src.ui.views_recipes import render_recipes_view


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
    if "shopping_df" not in st.session_state:
        st.session_state["shopping_df"] = None
    if "restaurant_name" not in st.session_state:
        st.session_state["restaurant_name"] = "Restaurante & Bar Central"
    if "periodo_label" not in st.session_state:
        st.session_state["periodo_label"] = "Fin de Semana (Viernes a Domingo)"
    if "margen_pct" not in st.session_state:
        st.session_state["margen_pct"] = 15


def render_financial_dashboard_tab(
    forecasting_engine: ForecastingEngine,
    procurement_service: ProcurementService
):
    """Pestaña 3: Dashboard de Métricas Financieras Primarias y Alertas Operativas."""
    st.markdown(f'<div class="main-header">💰 Dashboard Financiero ($ CLP) | {APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Métricas financieras primarias, detección de fugas de dinero por merma y decisiones operativas en tiempo real.</div>',
        unsafe_allow_html=True
    )

    sales_df = st.session_state.get("sales_df")
    if sales_df is None or sales_df.empty:
        st.warning("⚠️ Para ver las métricas financieras, primero sube tu archivo CSV o presiona 'Usar Datos Demo de 90 Días' en la Pestaña 1.")
        return

    # Controles Superiores de Gestión
    col_c1, col_c2, col_c3 = st.columns([1.2, 1.2, 1.2])

    with col_c1:
        filtro_horizonte = st.radio(
            "📅 Período de Abastecimiento:",
            options=["🎯 Solo Fin de Semana (Vie - Sáb - Dom)", "🗓️ Próximos 7 Días Corridos"],
            index=0,
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

    # Proyección y compras
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
        st.error("No se pudieron generar compras. Asegúrate de tener escandallos guardados en la Pestaña 2.")
        return

    # Cálculo de Métricas Financieras Primarias
    fin_kpis = procurement_service.calculate_financial_kpis(shopping_df, forecast_df, is_weekend_only=solo_fin_semana)
    alerts = procurement_service.get_operational_alerts(shopping_df)

    ahorro_mes_str = f"${int(fin_kpis['ahorro_mes_clp']):,}".replace(",", ".")
    puntos_fuga_str = f"${int(fin_kpis['puntos_fuga_clp']):,}".replace(",", ".")
    total_orden_str = f"${int(fin_kpis['total_orden_clp']):,}".replace(",", ".")
    ventas_est_str = f"${int(fin_kpis['ventas_proyectadas_clp']):,}".replace(",", ".")

    st.markdown("---")

    # 1. TARJETAS KPI FINANCIERAS (SECCIÓN SUPERIOR)
    st.subheader("💵 Métricas Financieras Primarias")

    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)

    with col_kpi1:
        render_financial_hero_card(
            title="Ahorro Comprobado del Mes ($ CLP)",
            value=f"{ahorro_mes_str} CLP",
            caption="Diferencia real entre compras intuitivas sin control y compras optimizadas.",
            badge="🟢 +15% EFICIENCIA",
            theme="green"
        )

    with col_kpi2:
        render_financial_hero_card(
            title="Puntos de Fuga de Dinero ($ CLP)",
            value=f"{puntos_fuga_str} CLP",
            caption="Capital en insumos perecibles (<48h) en riesgo de merma si no se rota a tiempo.",
            badge="🔴 CAPITAL EN RIESGO",
            theme="red"
        )

    with col_kpi3:
        render_financial_hero_card(
            title="Food Cost Proyectado (%)",
            value=f"{fin_kpis['food_cost_pct']:.1f}%",
            caption=f"Inversión de {total_orden_str} CLP sobre ventas estimadas de {ventas_est_str} CLP.",
            badge="🎯 RANGO ÓPTIMO (28% - 32%)",
            theme="blue"
        )

    st.markdown("---")

    # 2. SECCIÓN DE ALERTAS Y PUNTOS DE FUGA
    st.subheader("⚡ Alertas Operativas y Puntos de Fuga")
    st.markdown(
        "<span style='font-size: 0.92rem; color: #64748B;'>Decisiones prácticas para retener flujo de caja y evitar botar insumos a la basura.</span>",
        unsafe_allow_html=True
    )

    col_frena, col_promo = st.columns(2)

    with col_frena:
        frena_html = ""
        for item in alerts["frena_compras"]:
            frena_html += f"""
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
                {frena_html}
            </div>
        """, unsafe_allow_html=True)

    with col_promo:
        promo_html = ""
        for item in alerts["promociones"]:
            promo_html += f"""
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
                {promo_html}
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.info("👉 Para enviar las órdenes de compra divididas a cada distribuidor por WhatsApp, dirígete a la **Pestaña 4: Mis Proveedores**.")


def render_suppliers_tab(
    forecasting_engine: ForecastingEngine,
    procurement_service: ProcurementService
):
    """Pestaña 4: Mis Proveedores - Lista de Compras Agrupada y WhatsApp Independiente."""
    st.markdown(f'<div class="main-header">🚚 Mis Proveedores & Órdenes de Compra | {APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Módulo de Compras Limpias: Revisa los pedidos clasificados por centro de abastecimiento y genera el mensaje de WhatsApp independiente para cada distribuidor.</div>',
        unsafe_allow_html=True
    )

    sales_df = st.session_state.get("sales_df")
    if sales_df is None or sales_df.empty:
        st.warning("⚠️ Para revisar los pedidos por proveedor, primero carga tus ventas POS en la Pestaña 1.")
        return

    # Si aún no existe shopping_df en session_state, calcularlo
    shopping_df = st.session_state.get("shopping_df")
    solo_fin_semana = st.session_state.get("solo_fin_semana", True)
    margen_pct = st.session_state.get("margen_pct", 15)
    periodo_label = st.session_state.get("periodo_label", "Fin de Semana (Viernes a Domingo)")
    restaurant_name = st.session_state.get("restaurant_name", "Restaurante & Bar Central")

    if shopping_df is None or shopping_df.empty:
        max_date = pd.to_datetime(sales_df["fecha"]).dt.date.max()
        start_date = max_date + timedelta(days=1)
        forecast_df = forecasting_engine.project_next_days(
            sales_df,
            start_date=start_date,
            days_horizon=7,
            safety_margin=margen_pct / 100.0
        )
        st.session_state["forecast_df"] = forecast_df
        shopping_df = procurement_service.calculate_shopping_list(forecast_df, only_weekend=solo_fin_semana)
        st.session_state["shopping_df"] = shopping_df

    if shopping_df is None or shopping_df.empty:
        st.error("No se encontraron insumos para abastecer. Configura los escandallos en la Pestaña 2.")
        return

    # Resumen superior de proveedores
    proveedores_unicos = sorted(shopping_df["proveedor"].unique())
    total_general = int(shopping_df["subtotal_cost_clp"].sum())
    total_general_str = f"${total_general:,}".replace(",", ".")

    st.markdown(f"""
        <div style="background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 8px; padding: 14px 20px; margin-bottom: 16px;">
            <strong>📦 Resumen de Abastecimiento:</strong> {len(proveedores_unicos)} proveedores activos | 
            <strong>Inversión Total:</strong> <span style="color: #047857; font-weight: 700;">{total_general_str} CLP</span> |
            <strong>Período:</strong> {periodo_label}
        </div>
    """, unsafe_allow_html=True)

    # Iterar sobre cada proveedor de forma independiente
    for idx, prov in enumerate(proveedores_unicos):
        prov_df = shopping_df[shopping_df["proveedor"] == prov].copy()
        prov_subtotal = int(prov_df["subtotal_cost_clp"].sum())
        prov_subtotal_str = f"${prov_subtotal:,}".replace(",", ".")
        prov_slug = prov.split()[0].replace("🐟", "pesca").replace("🥩", "carne").replace("🥬", "vega").replace("🧀", "lacteo").replace("🏪", "gral")

        with st.container():
            st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; background: #FFFFFF; border: 1px solid #CBD5E1; border-left: 5px solid #0F172A; border-radius: 8px; padding: 12px 18px; margin-top: 14px; margin-bottom: 8px;">
                    <div>
                        <span style="font-size: 1.15rem; font-weight: 700; color: #0F172A;">{prov}</span>
                        <span style="font-size: 0.85rem; color: #64748B; margin-left: 10px;">({len(prov_df)} insumos)</span>
                    </div>
                    <div style="font-size: 1.1rem; font-weight: 800; color: #047857;">
                        Subtotal: {prov_subtotal_str} CLP
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Tabla limpia de compras por proveedor
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

            # Mensaje WhatsApp independiente para este proveedor
            wa_text_prov = procurement_service.format_supplier_whatsapp_message(
                supplier_name=prov,
                supplier_df=prov_df,
                restaurant_name=restaurant_name,
                periodo_label=periodo_label
            )

            col_btn1, col_btn2 = st.columns([1.5, 2.5])

            with col_btn1:
                btn_key = f"wa_btn_{idx}_{prov_slug}"
                if st.button(f"📋 Copiar pedido para WhatsApp", key=btn_key, use_container_width=True):
                    st.session_state[f"show_wa_{idx}"] = True
                    st.toast(f"✅ ¡Pedido para {prov} listo para copiar!")

            with col_btn2:
                encoded_msg = urllib.parse.quote(wa_text_prov)
                wa_url = f"https://wa.me/?text={encoded_msg}"
                st.link_button(f"📲 Abrir en WhatsApp Web ({prov.split('(')[0].strip()})", wa_url, use_container_width=True)

            with st.expander(f"👁️ Ver mensaje formateado para {prov}", expanded=st.session_state.get(f"show_wa_{idx}", False)):
                st.code(wa_text_prov, language="text")

        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 4. EXPORTACIONES FORMALES CONSOLIDADAS
    st.subheader(f"📄 Documentos Formales Consolidados ({APP_NAME})")
    col_doc1, col_doc2 = st.columns(2)

    legacy_metrics = procurement_service.calculate_waste_and_cost_metrics(shopping_df, is_weekend_only=solo_fin_semana)

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

    # Navegación por 4 pestañas operativas
    tab1, tab2, tab3, tab4 = st.tabs([
        "📂 Pestaña 1: Carga de Ventas POS",
        "🥗 Pestaña 2: Editor de Escandallos ($ CLP)",
        "💰 Pestaña 3: Dashboard de Ahorro y Fugas ($ CLP)",
        "🚚 Pestaña 4: Mis Proveedores (Compras & WhatsApp)"
    ])

    with tab1:
        render_pos_view(pos_parser, recipe_service)

    with tab2:
        render_recipes_view(recipe_service)

    with tab3:
        render_financial_dashboard_tab(forecasting_engine, procurement_service)

    with tab4:
        render_suppliers_tab(forecasting_engine, procurement_service)


if __name__ == "__main__":
    main()
