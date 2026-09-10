"""Vista 2: Editor interactivo de escandallos e insumos perecibles con costeo en pesos chilenos ($ CLP)."""

import streamlit as st
import pandas as pd
from src.services.recipe_service import RecipeService
from src.config import APP_NAME, DEFAULT_INGREDIENT_PRICES_CLP
from src.ui.components import render_info_banner, render_metric_card


def render_recipes_view(recipe_service: RecipeService):
    st.markdown(f'<div class="main-header">🥗 Editor de Escandallos e Insumos ($ CLP) | {APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Configura interactivamente la porción de insumo perecible que consume cada plato y su precio de compra en pesos chilenos ($ CLP).</div>',
        unsafe_allow_html=True
    )

    render_info_banner(
        "⚡ Editor Directo y Flexible",
        "Edita las celdas directamente en la tabla: modifica gramos por plato, agrega nuevos insumos o actualiza los precios en pesos chilenos ($ CLP). Al terminar, presiona <strong>💾 Guardar Cambios</strong>."
    )

    # Si hay platos detectados dinámicamente en el POS, sincronizarlos
    detected_dishes = st.session_state.get("detected_dishes")
    if detected_dishes:
        recipe_service.ensure_dishes_exist(detected_dishes)

    # Cargar datos actuales de escandallos
    recipes_df = recipe_service.to_dataframe()

    # Métricas de la carta
    platos_count = recipes_df["Plato"].nunique() if not recipes_df.empty else 0
    insumos_count = recipes_df["Insumo Perecible"].nunique() if not recipes_df.empty else 0
    precio_promedio = recipes_df["Precio Compra ($ CLP)"].mean() if not recipes_df.empty else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_card("Platos en Escandallo", str(platos_count), caption="Platos listos para proyectar")
    with c2:
        render_metric_card("Insumos Perecibles Únicos", str(insumos_count), caption="Materias primas controladas")
    with c3:
        precio_prom_str = f"${int(precio_promedio):,}".replace(",", ".")
        render_metric_card("Precio Promedio Insumos", f"{precio_prom_str} CLP", caption="Costo unitario referencial")

    st.markdown("---")
    st.subheader("📋 Tabla Interactiva de Escandallos y Costos")

    # Configuración de columnas para st.data_editor
    column_config = {
        "Plato": st.column_config.TextColumn(
            "Plato de la Carta",
            help="Nombre del plato vendido en el POS",
            required=True
        ),
        "Insumo Perecible": st.column_config.TextColumn(
            "Insumo Perecible Clave",
            help="Materia prima crítica que caduca rápido (ej: Reineta, Salmón, Lomo, Cebolla)",
            required=True
        ),
        "Dosis por Plato": st.column_config.NumberColumn(
            "Porción por Plato",
            help="Cantidad neta utilizada por porción",
            min_value=0.1,
            max_value=5000.0,
            step=10.0,
            required=True
        ),
        "Unidad Receta": st.column_config.SelectboxColumn(
            "Unidad Receta",
            options=["g", "ml", "un"],
            required=True
        ),
        "Precio Compra ($ CLP)": st.column_config.NumberColumn(
            "Precio Compra ($ CLP)",
            help="Costo de compra por kilo o por unidad en pesos chilenos ($ CLP)",
            min_value=0.0,
            step=500.0,
            format="$ %d",
            required=True
        ),
        "Unidad Compra": st.column_config.SelectboxColumn(
            "Unidad Compra",
            options=["kg", "L", "un"],
            required=True
        )
    }

    # Editor interactivo de Streamlit
    edited_df = st.data_editor(
        recipes_df,
        column_config=column_config,
        num_rows="dynamic",
        use_container_width=True,
        key="recipes_data_editor"
    )

    col_save, col_reset, col_space = st.columns([1.5, 1.5, 2])

    with col_save:
        if st.button("💾 Guardar Cambios en EZtock", type="primary", use_container_width=True):
            try:
                recipe_service.update_from_dataframe(edited_df)
                st.session_state["recipes_df"] = edited_df
                st.success("✅ ¡Escandallos y precios en CLP actualizados exitosamente en la sesión!")
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar los escandallos: {e}")

    with col_reset:
        if st.button("🔄 Restablecer a Escandallos Base", use_container_width=True):
            recipe_service.reset_to_defaults()
            st.success("Escandallos restablecidos a los valores base chilenos.")
            st.rerun()

    # Tip culinario y de costos
    st.markdown("""
        <div style="margin-top: 20px; padding: 12px 16px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;">
            <span style="font-weight: 600; color: #1E293B;">💡 Recomendación de Costeo Gastronómico:</span>
            <span style="font-size: 0.88rem; color: #64748B;"><br>
            Al ingresar el <strong>Precio Compra ($ CLP)</strong>, utiliza el valor neto pactado con tu distribuidor o feria (ej: Reineta $9.500 CLP/kg, Salmón $14.000 CLP/kg, Lomo Vacuno $9.800 CLP/kg). Esto permitirá calcular con exactitud el valor total de tu orden de compra y el ahorro mensual por merma prevenida.
            </span>
        </div>
    """, unsafe_allow_html=True)
