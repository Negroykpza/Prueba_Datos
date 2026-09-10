"""Vista 1: Carga y validación de archivos de ventas exportados desde sistemas POS."""

import streamlit as st
import pandas as pd
from src.services.pos_parser import POSParser
from src.config import SAMPLE_POS_PATH
from src.ui.components import render_metric_card, render_info_banner


def render_pos_view(pos_parser: POSParser):
    st.markdown('<div class="main-header">📂 Ingesta de Ventas POS</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Carga el reporte de ventas histórico de tu restaurante (Toteat, Bsale, Fudo, Loyverse o Excel).</div>',
        unsafe_allow_html=True
    )

    render_info_banner(
        "💡 Formato Requerido",
        "El archivo CSV debe contener al menos 3 columnas: <strong>Fecha</strong> (ej: 15/08/2026), <strong>Plato/Ítem</strong> (ej: Ceviche Mixto) y <strong>Cantidad Vendida</strong>."
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Selecciona tu archivo de ventas (.csv)",
            type=["csv"],
            help="Soporta separadores de coma (,) y punto y coma (;), y codificaciones UTF-8 y Latin-1."
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        cargar_demo = st.button("🚀 Cargar Datos Demo (Cevichería / Restobar)", use_container_width=True)

    # Procesar archivo cargado o demo
    if uploaded_file is not None:
        try:
            file_bytes = uploaded_file.getvalue()
            df, summary = pos_parser.load_from_bytes(file_bytes)
            st.session_state["sales_df"] = df
            st.session_state["pos_summary"] = summary
            st.success(f"✅ Archivo '{uploaded_file.name}' cargado y normalizado correctamente.")
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo CSV: {str(e)}")

    elif cargar_demo:
        if SAMPLE_POS_PATH.exists():
            try:
                df, summary = pos_parser.load_from_path(SAMPLE_POS_PATH)
                st.session_state["sales_df"] = df
                st.session_state["pos_summary"] = summary
                st.success("✅ Dataset de demostración cargado con éxito (60 días de operación).")
            except Exception as e:
                st.error(f"❌ Error al cargar datos demo: {str(e)}")
        else:
            st.error("No se encontró el archivo de datos demo.")

    # Mostrar métricas y vista previa si existen datos
    if "sales_df" in st.session_state and st.session_state["sales_df"] is not None:
        df = st.session_state["sales_df"]
        summary = st.session_state.get("pos_summary", {})

        st.markdown("---")
        st.subheader("📊 Resumen del Historial Procesado")

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
                "Platos Distintos",
                str(summary.get("platos_unicos", 0)),
                caption="Ítems únicos en la carta"
            )
        with m4:
            f_ini = summary.get("fecha_inicio")
            f_fin = summary.get("fecha_fin")
            rango_str = f"{f_ini.strftime('%d/%m/%y')} al {f_fin.strftime('%d/%m/%y')}" if f_ini and f_fin else "-"
            render_metric_card(
                "Período Analizado",
                rango_str,
                caption="Rango de fechas procesado"
            )

        # Vista previa de datos
        with st.expander("🔍 Ver tabla de ventas normalizada (Primeras 50 filas)", expanded=False):
            st.dataframe(df.head(50), use_container_width=True)
            csv_export = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Descargar Datos Normalizados (CSV)",
                data=csv_export,
                file_name="ventas_pos_normalizadas.csv",
                mime="text/csv"
            )
    else:
        st.info("👆 Por favor, sube un archivo CSV o haz clic en 'Cargar Datos Demo' para comenzar.")
