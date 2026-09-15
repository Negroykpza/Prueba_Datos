"""Vista 2: Editor Dinámico e Interactivo de Recetas e Insumos por Plato ($ CLP) para EZtock."""

import streamlit as st
import pandas as pd
from src.services.recipe_service import RecipeService
from src.config import APP_NAME, TAB_OPTIONS, set_active_tab
from src.ui.components import render_info_banner, render_metric_card


def render_recipes_view(recipe_service: RecipeService):
    st.markdown(f'<div class="main-header">🥗 Recetas e Insumos por Plato | {APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Gestiona los ingredientes por plato y el costo de compra en pesos chilenos ($ CLP).</div>',
        unsafe_allow_html=True
    )

    render_info_banner(
        "⚡ Editor Directo y Flexible de Ingredientes",
        "Edita las celdas directamente en la tabla: modifica gramos o porciones por plato, agrega nuevos insumos o actualiza los precios en pesos chilenos (<code>$ CLP</code>). Al terminar, presiona <strong>💾 Guardar Cambios</strong>."
    )

    # Si hay platos detectados dinámicamente en el POS, sincronizarlos
    detected_dishes = st.session_state.get("detected_dishes", [])
    if detected_dishes:
        recipe_service.sync_with_detected_dishes(detected_dishes)

    # Cargar datos actuales de recetas
    recipes_df = recipe_service.to_dataframe()

    # Métricas enriquecidas de la carta en Dark Mode
    platos_count = recipes_df["Plato"].nunique() if not recipes_df.empty else 0
    insumos_count = recipes_df["Insumo Perecible"].nunique() if not recipes_df.empty else 0
    precio_promedio = recipes_df["Precio Compra ($ CLP)"].mean() if not recipes_df.empty else 0
    precio_prom_str = f"${int(precio_promedio):,}".replace(",", ".")

    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_card(
            title="Platos con Receta",
            value=str(platos_count),
            delta="100% Mapeados",
            delta_type="positive",
            caption="Platos listos para proyectar"
        )
    with c2:
        render_metric_card(
            title="Insumos Perecibles Únicos",
            value=str(insumos_count),
            delta="Control 80/20",
            delta_type="neutral",
            caption="Materias primas clave"
        )
    with c3:
        render_metric_card(
            title="Precio Promedio Insumos",
            value=f"{precio_prom_str} CLP",
            delta="Costo Base",
            delta_type="neutral",
            caption="Costo unitario referencial"
        )

    st.markdown("---")
    st.subheader("📋 Tabla Interactiva de Ingredientes y Costos por Plato")
    st.markdown("<span style='font-size: 0.88rem; color: #94A3B8;'>Modifica los valores directamente o presiona '+' abajo para agregar nuevos ingredientes a cualquier plato:</span>", unsafe_allow_html=True)

    # Configuración de columnas para st.data_editor
    column_config = {
        "Plato": st.column_config.TextColumn(
            "Plato de la Carta",
            help="Nombre del plato según la carta o el sistema POS.",
            required=True,
            width="medium"
        ),
        "Insumo Perecible": st.column_config.TextColumn(
            "Insumo Perecible",
            help="Ingrediente crítico con riesgo de descomposición o merma (ej: carnes, pescados, verduras).",
            required=True,
            width="medium"
        ),
        "Cantidad": st.column_config.NumberColumn(
            "Porción por Plato",
            help="Cantidad de insumo que lleva cada plato.",
            min_value=0.01,
            max_value=10000.0,
            step=0.01,
            format="%.2f",
            required=True,
            width="small"
        ),
        "Unidad": st.column_config.SelectboxColumn(
            "Unidad",
            help="Unidad de medida de la porción en la receta.",
            options=["gramos", "kg", "unidades", "ml", "litros"],
            required=True,
            width="small"
        ),
        "Precio Compra ($ CLP)": st.column_config.NumberColumn(
            "Precio Compra ($ CLP)",
            help="Precio neto que pagas por Kilo, Litro o Unidad a tu proveedor en Chile.",
            min_value=100,
            max_value=500000,
            step=500,
            format="$%d CLP",
            required=True,
            width="medium"
        )
    }

    # Editor interactivo
    edited_df = st.data_editor(
        recipes_df,
        column_config=column_config,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="recipes_data_editor",
        height=380
    )

    col_btn_save, col_btn_reset, _ = st.columns([1.2, 1.2, 2.5])

    with col_btn_save:
        if st.button("💾 Guardar Cambios en Recetas", type="primary", use_container_width=True):
            recipe_service.update_from_dataframe(edited_df)
            st.success("✅ ¡Recetas y precios en $ CLP guardados exitosamente!")
            st.toast("✅ Recetas e ingredientes actualizados para el cálculo de compras.")

    with col_btn_reset:
        if st.button("🔄 Restaurar Valores por Defecto", use_container_width=True):
            recipe_service.reset_to_defaults()
            st.warning("⚠️ Se restauraron las recetas y precios de compra base en $ CLP.")
            st.rerun()

    # Tip culinario y de costos en Dark Mode
    st.markdown("""
        <div class="banner-tip-dark" style="margin-top: 20px;">
            <strong>💡 Recomendación de Costeo Gastronómico:</strong><br>
            Al ingresar el <strong>Precio Compra ($ CLP)</strong>, utiliza el valor neto pactado con tu distribuidor o feria (ej: Reineta $9.500 CLP/kg, Salmón $14.000 CLP/kg, Lomo Vacuno $9.800 CLP/kg). Esto permitirá calcular con exactitud el valor total de tu orden de compra en las Pestañas 3 y 4, así como el ahorro mensual por merma prevenida.
        </div>
    """, unsafe_allow_html=True)

    # Botón CTA hacia la Pestaña 3 con callback seguro on_click
    st.markdown('<div class="cta-container">', unsafe_allow_html=True)
    col_spacer, col_cta = st.columns([1.5, 1])
    with col_cta:
        st.button(
            "Continuar a Dashboard Financiero & Fugas ($ CLP) ➡️",
            type="primary",
            use_container_width=True,
            on_click=set_active_tab,
            args=(TAB_OPTIONS[2],)
        )
    st.markdown('</div>', unsafe_allow_html=True)
