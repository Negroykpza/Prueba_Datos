"""Vista 2: Configuración de recetas para los 5 insumos perecibles más críticos."""

import streamlit as st
import pandas as pd
from src.services.recipe_service import RecipeService
from src.models.schema import Recipe, IngredientRequirement
from src.ui.components import render_info_banner, render_metric_card


# Catálogo de los 5 insumos perecibles más críticos de la gastronomía chilena
CRITICAL_PERISHABLES = [
    {
        "id": "pescado_blanco",
        "name": "Pescado Blanco Fresco (Reineta)",
        "emoji": "🐟",
        "shelf_life": "24 - 48 horas",
        "risk_level": "CRÍTICO",
        "risk_badge_color": "#EF4444",
        "unit": "kg",
        "cost_ref": "$9.500 CLP/kg",
        "default_dose": 180.0,
        "default_unit": "g"
    },
    {
        "id": "salmon",
        "name": "Filete de Salmón Fresco",
        "emoji": "🍣",
        "shelf_life": "48 horas",
        "risk_level": "CRÍTICO",
        "risk_badge_color": "#EF4444",
        "unit": "kg",
        "cost_ref": "$14.000 CLP/kg",
        "default_dose": 220.0,
        "default_unit": "g"
    },
    {
        "id": "lomo_vacuno",
        "name": "Lomo Liso Vacuno",
        "emoji": "🥩",
        "shelf_life": "3 - 5 días",
        "risk_level": "MEDIO-ALTO",
        "risk_badge_color": "#F59E0B",
        "unit": "kg",
        "cost_ref": "$9.800 CLP/kg",
        "default_dose": 220.0,
        "default_unit": "g"
    },
    {
        "id": "cebolla_morada",
        "name": "Cebolla Morada",
        "emoji": "🧅",
        "shelf_life": "2 - 4 días (picada)",
        "risk_level": "MEDIO",
        "risk_badge_color": "#10B981",
        "unit": "kg",
        "cost_ref": "$1.200 CLP/kg",
        "default_dose": 50.0,
        "default_unit": "g"
    },
    {
        "id": "limon_sutil",
        "name": "Limón Sutil",
        "emoji": "🍋",
        "shelf_life": "5 - 7 días",
        "risk_level": "MEDIO",
        "risk_badge_color": "#10B981",
        "unit": "un",
        "cost_ref": "$1.800 CLP/malla",
        "default_dose": 4.0,
        "default_unit": "un"
    }
]


def render_recipes_view(recipe_service: RecipeService):
    st.markdown('<div class="main-header">🥗 Configuración de Escandallos: 5 Insumos Críticos</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Gestiona las dosis técnicas de los 5 insumos perecibles que concentran el 80% de las mermas por caducidad en restaurantes chilenos.</div>',
        unsafe_allow_html=True
    )

    render_info_banner(
        "🎯 Principio del 80/20 Gastronómico",
        "El desperdicio no se produce en el arroz ni en las especias. Ocurre en <strong>pescados frescos, carnes rojas y verduras picadas</strong> que no se alcanzan a vender el fin de semana y deben botarse el lunes."
    )

    # 1. Resumen de los 5 insumos críticos
    st.subheader("📌 Los 5 Insumos Perecibles Más Críticos")
    cols = st.columns(5)
    for idx, item in enumerate(CRITICAL_PERISHABLES):
        with cols[idx]:
            st.markdown(f"""
                <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; text-align: center; height: 100%;">
                    <div style="font-size: 1.8rem;">{item['emoji']}</div>
                    <div style="font-weight: 700; font-size: 0.85rem; color: #1E293B; margin-top: 4px;">{item['name']}</div>
                    <div style="font-size: 0.75rem; color: #64748B;">Caducidad: {item['shelf_life']}</div>
                    <div style="margin-top: 6px; display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; background-color: {item['risk_badge_color']}20; color: {item['risk_badge_color']};">
                        {item['risk_level']}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    tab_criticos, tab_tabla_completa, tab_nuevo = st.tabs([
        "⚙️ Ajustar Dosis de Insumos Críticos",
        "📋 Catálogo Completo de Escandallos",
        "➕ Asociar Nuevo Plato a Insumo Crítico"
    ])

    all_recipes = recipe_service.get_all_recipes()

    # Pestaña A: Ajuste rápido de dosis en platos existentes
    with tab_criticos:
        st.markdown("##### Selecciona un insumo para ajustar los gramos o unidades por plato:")
        selected_ing_name = st.selectbox(
            "Insumo Crítico a configurar:",
            options=[item["name"] for item in CRITICAL_PERISHABLES]
        )

        # Buscar qué platos usan actualmente este insumo
        platos_asociados = []
        for r in all_recipes:
            for ing in r.ingredients:
                if selected_ing_name.lower() in ing.ingredient_name.lower() or ing.ingredient_name.lower() in selected_ing_name.lower():
                    platos_asociados.append((r, ing))

        if platos_asociados:
            st.write(f"Este insumo se utiliza actualmente en **{len(platos_asociados)} platos** de la carta:")
            for recipe, ing in platos_asociados:
                c_plato, c_dosis, c_unidad, c_btn = st.columns([3, 2, 2, 1.5])
                with c_plato:
                    st.text_input("Plato:", value=recipe.dish_name, disabled=True, key=f"p_{recipe.dish_name}")
                with c_dosis:
                    nueva_dosis = st.number_input(
                        f"Dosis ({ing.recipe_unit}):",
                        min_value=0.1,
                        value=float(ing.quantity_per_dish),
                        step=5.0,
                        key=f"d_{recipe.dish_name}_{ing.ingredient_name}"
                    )
                with c_unidad:
                    st.text_input("Unidad de Compra:", value=ing.purchase_unit, disabled=True, key=f"u_{recipe.dish_name}")
                with c_btn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Actualizar", key=f"b_{recipe.dish_name}_{ing.ingredient_name}"):
                        ing.quantity_per_dish = nueva_dosis
                        recipe_service.upsert_recipe(recipe)
                        st.success(f"Dosis de {recipe.dish_name} actualizada a {nueva_dosis}{ing.recipe_unit}")
                        st.rerun()
        else:
            st.info(f"Ningún plato tiene asignado actualmente '{selected_ing_name}'. Puedes asociarlo en la pestaña '➕ Asociar Nuevo Plato a Insumo Crítico'.")

    # Pestaña B: Tabla general de escandallos
    with tab_tabla_completa:
        recipes_df = recipe_service.to_dataframe()
        if not recipes_df.empty:
            st.dataframe(recipes_df, use_container_width=True)
            col_b1, col_b2 = st.columns([3, 1])
            with col_b2:
                if st.button("🔄 Restablecer a Escandallos Base", use_container_width=True):
                    recipe_service.reset_to_defaults()
                    st.success("Recetas restablecidas a valores base.")
                    st.rerun()
        else:
            st.info("No hay recetas registradas.")

    # Pestaña C: Agregar nuevo plato asociado a uno de los 5 insumos críticos
    with tab_nuevo:
        st.markdown("##### Crear o Editar Plato con Insumo Crítico")

        sales_df = st.session_state.get("sales_df")
        sugerencias_platos = sorted(sales_df["plato"].unique()) if sales_df is not None else []

        col_d1, col_d2 = st.columns([2, 1])
        with col_d1:
            if sugerencias_platos:
                opcion = st.selectbox("Seleccionar plato existente en POS o escribir uno nuevo:", ["-- Escribir nuevo --"] + sugerencias_platos)
                nombre_plato = st.text_input("Nombre del plato:", value="" if opcion == "-- Escribir nuevo --" else opcion).strip()
            else:
                nombre_plato = st.text_input("Nombre del plato (ej: Ceviche Mixto):", value="").strip()
        with col_d2:
            categoria_plato = st.selectbox("Categoría:", ["Pescados y Mariscos", "Carnes", "Entradas", "Platos Chilenos", "Otro"])

        st.markdown("##### Insumo Crítico Principal")
        col_i1, col_i2, col_i3 = st.columns([2, 1.5, 1])
        with col_i1:
            insumo_critico_elegido = st.selectbox("Selecciona uno de los 5 insumos críticos:", options=[item["name"] for item in CRITICAL_PERISHABLES])
        with col_i2:
            meta = next(item for item in CRITICAL_PERISHABLES if item["name"] == insumo_critico_elegido)
            dosis_val = st.number_input(f"Dosis por porción ({meta['default_unit']}):", min_value=0.1, value=float(meta["default_dose"]), step=5.0)
        with col_i3:
            st.text_input("Unidad Compra:", value=meta["unit"], disabled=True)

        if st.button("💾 Guardar Escandallo", type="primary"):
            if not nombre_plato:
                st.error("Ingresa el nombre del plato.")
            else:
                factor = 0.001 if meta["default_unit"] == "g" and meta["unit"] == "kg" else 1.0
                nuevo_ing = IngredientRequirement(
                    ingredient_name=insumo_critico_elegido,
                    quantity_per_dish=dosis_val,
                    recipe_unit=meta["default_unit"],
                    purchase_unit=meta["unit"],
                    conversion_factor=factor
                )
                rec = recipe_service.get_recipe(nombre_plato) or Recipe(dish_name=nombre_plato, categoria=categoria_plato, ingredients=[])
                # Reemplazar si ya existía el insumo o agregarlo
                rec.ingredients = [i for i in rec.ingredients if i.ingredient_name != insumo_critico_elegido] + [nuevo_ing]
                rec.categoria = categoria_plato
                recipe_service.upsert_recipe(rec)
                st.success(f"Escandallo de '{nombre_plato}' guardado exitosamente!")
                st.rerun()
