"""Vista 4: Gestión de Proveedores, Pedidos Independientes por WhatsApp y Documentos Formales para EZtock."""

import urllib.parse
from datetime import timedelta
import streamlit as st
import pandas as pd
from src.services.forecasting import ForecastingEngine
from src.services.procurement import ProcurementService
from src.config import APP_NAME


def render_suppliers_view(
    forecasting_engine: ForecastingEngine,
    procurement_service: ProcurementService
):
    """Pestaña 4: Mis Proveedores (Lista de Compras agrupada y WhatsApp independiente)."""
    st.markdown(f'<div class="main-header">🚚 Mis Proveedores & Órdenes de Compra | {APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Lista de compras segmentada por distribuidor: envía pedidos independientes por WhatsApp con un solo clic o descarga reportes formales.</div>',
        unsafe_allow_html=True
    )

    sales_df = st.session_state.get("sales_df")
    if sales_df is None or sales_df.empty:
        st.warning("⚠️ Para generar las compras por proveedor, primero sube tu archivo CSV o presiona 'Usar Datos Demo de 90 Días' en la Pestaña 1.")
        return

    # Obtener o calcular shopping_df
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
        st.error("No se encontraron insumos para abastecer. Configura las recetas e ingredientes en la Pestaña 2.")
        return

    # Resumen superior de proveedores con componentes nativos
    proveedores_unicos = sorted(shopping_df["proveedor"].unique())
    total_general = int(shopping_df["subtotal_cost_clp"].sum())
    total_general_str = f"${total_general:,}".replace(",", ".")

    with st.container(border=True):
        col_res1, col_res2, col_res3 = st.columns(3)
        with col_res1:
            st.metric("📦 Proveedores Activos", f"{len(proveedores_unicos)} distribuidores")
        with col_res2:
            st.metric("💰 Inversión Total Pedido", f"{total_general_str} CLP")
        with col_res3:
            st.metric("📅 Período de Entrega", periodo_label)

    # Iterar sobre cada proveedor de forma independiente con tarjetas nativas
    for idx, prov in enumerate(proveedores_unicos):
        prov_df = shopping_df[shopping_df["proveedor"] == prov].copy()
        prov_subtotal = int(prov_df["subtotal_cost_clp"].sum())
        prov_subtotal_str = f"${prov_subtotal:,}".replace(",", ".")
        prov_slug = prov.split()[0].replace("🐟", "pesca").replace("🥩", "carne").replace("🥬", "vega").replace("🧀", "lacteo").replace("🏪", "gral")

        with st.container(border=True):
            col_header1, col_header2 = st.columns([3, 1.5])
            with col_header1:
                st.markdown(f"### {prov}")
                st.caption(f"{len(prov_df)} materias primas requeridas")
            with col_header2:
                st.metric("Subtotal Proveedor", f"{prov_subtotal_str} CLP")

            # Tabla de compras por proveedor
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
                use_container_width=True,
                hide_index=True
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

    st.markdown("---")

    # Documentos Formales Consolidados (PDF y Excel)
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
