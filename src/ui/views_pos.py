"""Vista 1: Carga, validación y detección dinámica de platos desde cualquier archivo CSV de ventas POS."""

import streamlit as st
import pandas as pd
from src.services.pos_parser import POSParser
from src.services.recipe_service import RecipeService
from src.config import SAMPLE_POS_PATH, APP_NAME
from src.ui.components import render_metric_card, render_info_banner


def render_pos_view(pos_parser: POSParser, recipe_service: RecipeService):
    st.markdown(f'<div class="main-header">📂 Ingesta y Detección de Ventas POS | {APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Sube cualquier archivo CSV de ventas de tu restaurante (Toteat, Bsale, Fudo, Loyverse o Excel). EZtock detectará los platos y columnas automáticamente.</div>',
        unsafe_allow_html=True
    )

    render_info_banner(
        "💡 Compatibilidad Dinámica",
        "Sube tu archivo con columnas de <strong>Fecha</strong>, <strong>Plato/Producto</strong> y <strong>Cantidad Vendida</strong>. EZtock detectará de forma automática los platos únicos de tu carta para configurar escandallos y calcular compras."
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Selecciona cualquier archivo CSV de ventas:",
            type=["csv"],
            help="Soporta separadores de coma (,), punto y coma (;) y codificaciones UTF-8 y Latin-1."
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        cargar_demo = st.button("🚀 Usar Datos Demo de 90 Días (Chile)", use_container_width=True)

    # Procesar archivo cargado o demo
    if uploaded_file is not None:
        try:
            file_bytes = uploaded_file.getvalue()
            df, summary = pos_parser.load_from_bytes(file_bytes)
            st.session_state["sales_df"] = df
            st.session_state["pos_summary"] = summary

            # Detección dinámica de platos únicos
            detected_dishes = sorted(df["plato"].unique().tolist())
            st.session_state["detected_dishes"] = detected_dishes
            recipe_service.ensure_dishes_exist(detected_dishes)

            st.success(f"✅ Archivo '{uploaded_file.name}' procesado con éxito. Se detectaron {len(detected_dishes)} platos dinámicamente.")
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo CSV: {str(e)}")

    elif cargar_demo:
        if SAMPLE_POS_PATH.exists():
            try:
                df, summary = pos_parser.load_from_path(SAMPLE_POS_PATH)
                st.session_state["sales_df"] = df
                st.session_state["pos_summary"] = summary

                detected_dishes = sorted(df["plato"].unique().tolist())
                st.session_state["detected_dishes"] = detected_dishes
                recipe_service.ensure_dishes_exist(detected_dishes)

                st.success(f"✅ Datos de demostración cargados (90 días). Se detectaron {len(detected_dishes)} platos chilenos.")
            except Exception as e:
                st.error(f"❌ Error al cargar datos demo: {str(e)}")
        else:
            st.error("No se encontró el archivo de datos demo.")

    # Mostrar métricas y platos detectados
    if "sales_df" in st.session_state and st.session_state["sales_df"] is not None:
        df = st.session_state["sales_df"]
        summary = st.session_state.get("pos_summary", {})
        detected = st.session_state.get("detected_dishes", sorted(df["plato"].unique().tolist()))

        st.markdown("---")
        st.subheader("📊 Diagnóstico del Archivo Cargado")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            render_metric_card(
                "Total Unidades Vendidas",
                f"{int(summary.get('total_unidades_vendidas', 0)):,}".replace(",", "."),
                caption="Volumen total en período"
            )
        with m2:
            render_metric_card(
                "Días Operativos",
                str(summary.get("dias_totales", 0)),
                caption="Días con registro de ventas"
            )
        with m3:
            render_metric_card(
                "Platos Únicos Detectados",
                str(len(detected)),
                caption="Identificados dinámicamente",
                delta_color="#3B82F6"
            )
        with m4:
            f_ini = summary.get("fecha_inicio")
            f_fin = summary.get("fecha_fin")
            rango_str = f"{f_ini.strftime('%d/%m/%y')} al {f_fin.strftime('%d/%m/%y')}" if f_ini and f_fin else "-"
            render_metric_card(
                "Período Analizado",
                rango_str,
                caption="Ventana histórica de fechas"
            )

        # Mostrar platos detectados en chips/badges interactivos
        st.markdown("##### 🍽️ Platos Detectados en tu Carta:")
        chips_html = "".join([
            f'<span style="display: inline-block; background-color: #EEF2F6; color: #1E293B; border: 1px solid #CBD5E1; padding: 4px 10px; border-radius: 16px; margin: 3px 5px; font-size: 0.85rem; font-weight: 500;">🍽️ {dish}</span>'
            for dish in detected
        ])
        st.markdown(f'<div style="margin-bottom: 15px;">{chips_html}</div>', unsafe_allow_html=True)

        # Vista previa de datos
        with st.expander("🔍 Ver registros normalizados (Primeras 50 filas)", expanded=False):
            st.dataframe(df.head(50), use_container_width=True)
            csv_export = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Descargar Datos Normalizados (CSV)",
                data=csv_export,
                file_name="ventas_normalizadas_eztock.csv",
                mime="text/csv"
            )
    else:
        st.info("👆 Sube tu archivo CSV o presiona 'Usar Datos Demo' para que EZtock detecte tus platos y comience el análisis.")
