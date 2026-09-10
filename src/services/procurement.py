"""Servicio de cálculo de requerimientos de materias primas, estimación de mermas y exportación (WhatsApp, Excel, PDF)."""

import io
from typing import Dict, List, Optional, Tuple
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from src.services.recipe_service import RecipeService


# Costo promedio referencial por kg de insumos en ferias mayoristas de Chile (CLP)
ESTIMATED_COST_PER_KG_CLP = {
    "pescado": 9500,    # Reineta / Corvina fresca
    "salmón": 14000,    # Filete de salmón
    "vacuno": 9800,     # Lomo liso / posta
    "pollo": 4800,      # Pechuga
    "atún": 13500,      # Atún fresco
    "machas": 8500,     # Machas
    "cebolla": 1200,    # Saco cebolla morada
    "limón": 1800,      # Malla limón sutil
    "default": 6500     # Promedio ponderado general
}

# Niveles de riesgo de merma por caducidad
SHELF_LIFE_RISK = {
    "Pescado Blanco Fresco (Reineta)": ("CRÍTICO", "Vida útil 24-48h refrigerado", "#EF4444"),
    "Filete de Salmón Fresco": ("CRÍTICO", "Vida útil 48h refrigerado", "#EF4444"),
    "Atún Fresco": ("CRÍTICO", "Consumo en 24-48h", "#EF4444"),
    "Lenguas de Machas Frescas": ("CRÍTICO", "Consumo en 24-48h", "#EF4444"),
    "Lomo Liso Vacuno": ("MEDIO", "Vida útil 3-5 días refrigerado", "#F59E0B"),
    "Carne Picada Vacuno (Posta)": ("MEDIO", "Vida útil 2-3 días refrigerado", "#F59E0B"),
    "Corte de Vacuno (Osobuco/Tapa Pecho)": ("MEDIO", "Vida útil 3-5 días refrigerado", "#F59E0B"),
    "Cebolla Morada": ("BAJO", "Vida útil > 7 días en bodega fresca", "#10B981"),
    "Cebolla Picada": ("MEDIO", "Vida útil 2-3 días refrigerada", "#F59E0B"),
    "Limón Sutil": ("BAJO", "Vida útil 5-8 días", "#10B981"),
    "Palta Hass": ("ALTO", "Maduración rápida: 2-3 días", "#F97316")
}


class ProcurementService:
    """Traduce la proyección de platos a volúmenes de compra de insumos perecibles (kg/unidades)."""

    def __init__(self, recipe_service: RecipeService):
        self.recipe_service = recipe_service

    def calculate_shopping_list(
        self,
        forecast_df: pd.DataFrame,
        only_weekend: bool = True
    ) -> pd.DataFrame:
        """
        Calcula la lista de compras agrupada por insumo perecible para el período proyectado.
        Si only_weekend=True, considera únicamente las ventas de Viernes, Sábado y Domingo.
        """
        if forecast_df.empty:
            return pd.DataFrame()

        df = forecast_df.copy()
        if only_weekend:
            df = df[df["es_fin_de_semana"]].copy()

        if df.empty:
            return pd.DataFrame()

        # Agrupar demanda por plato en el período seleccionado
        dish_totals = (
            df.groupby("plato", as_index=False)
            .agg({
                "demanda_base": "sum",
                "margen_seguridad_unidades": "sum",
                "demanda_con_margen": "sum"
            })
        )

        ingredient_records: List[Dict] = []

        for _, row in dish_totals.iterrows():
            dish_name = row["plato"]
            recipe = self.recipe_service.get_recipe(dish_name)
            if not recipe or not recipe.ingredients:
                continue

            for ing in recipe.ingredients:
                factor = ing.conversion_factor
                base_qty = row["demanda_base"] * ing.quantity_per_dish * factor
                margin_qty = row["margen_seguridad_unidades"] * ing.quantity_per_dish * factor
                total_qty = row["demanda_con_margen"] * ing.quantity_per_dish * factor

                ingredient_records.append({
                    "insumo": ing.ingredient_name,
                    "unidad": ing.purchase_unit,
                    "plato_origen": dish_name,
                    "consumo_base": base_qty,
                    "margen_seguridad": margin_qty,
                    "total_sugerido": total_qty
                })

        if not ingredient_records:
            return pd.DataFrame()

        ing_df = pd.DataFrame(ingredient_records)

        # Agrupar por insumo y unidad de compra
        aggregated = (
            ing_df.groupby(["insumo", "unidad"], as_index=False)
            .agg({
                "consumo_base": "sum",
                "margen_seguridad": "sum",
                "total_sugerido": "sum",
                "plato_origen": lambda dishes: ", ".join(sorted(set(dishes)))
            })
            .rename(columns={"plato_origen": "platos_asociados"})
            .sort_values(by="total_sugerido", ascending=False)
            .reset_index(drop=True)
        )

        # Redondear valores
        aggregated["consumo_base"] = aggregated["consumo_base"].round(2)
        aggregated["margen_seguridad"] = aggregated["margen_seguridad"].round(2)
        aggregated["total_sugerido"] = aggregated["total_sugerido"].round(2)

        # Asignar riesgo de caducidad
        def get_risk(insumo_name: str) -> Tuple[str, str]:
            for key, (level, desc, _) in SHELF_LIFE_RISK.items():
                if key.lower() in insumo_name.lower() or insumo_name.lower() in key.lower():
                    return level, desc
            return "MEDIO", "Perecible estándar"

        risk_data = [get_risk(name) for name in aggregated["insumo"]]
        aggregated["riesgo_caducidad"] = [r[0] for r in risk_data]
        aggregated["detalle_riesgo"] = [r[1] for r in risk_data]

        return aggregated

    def calculate_waste_metrics(self, shopping_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calcula las métricas de merma estimada y ahorro en Food Cost.
        En restaurantes sin planificación predictiva, el sobrestock de fin de semana
        provoca mermas típicas del 15% al 25% del volumen comprado que se descarta el lunes.
        """
        if shopping_df.empty:
            return {
                "kg_en_riesgo": 0.0,
                "kg_ahorro_merma": 0.0,
                "ahorro_clp": 0.0,
                "porcentaje_reduccion_merma": 65.0
            }

        kg_df = shopping_df[shopping_df["unidad"] == "kg"]
        total_kg = kg_df["total_sugerido"].sum() if not kg_df.empty else 0.0

        # Estimación conservadora:
        # - Compra intuitiva tradicional genera ~18% de sobrestock no vendido que caduca.
        # - Con el colchón ajustado del 15%, la merma por descomposición cae a menos del 5%.
        # - Ahorro neto en merma: ~13% del volumen total en kg.
        kg_ahorro = total_kg * 0.13
        kg_en_riesgo = total_kg * 0.18

        # Estimación monetaria en CLP
        ahorro_clp = 0.0
        for _, row in kg_df.iterrows():
            name = row["insumo"].lower()
            kg_val = row["total_sugerido"] * 0.13
            cost_per_kg = ESTIMATED_COST_PER_KG_CLP["default"]
            for key, cost in ESTIMATED_COST_PER_KG_CLP.items():
                if key in name:
                    cost_per_kg = cost
                    break
            ahorro_clp += kg_val * cost_per_kg

        return {
            "total_kg_compras": round(total_kg, 1),
            "kg_en_riesgo": round(kg_en_riesgo, 1),
            "kg_ahorro_merma": round(kg_ahorro, 1),
            "ahorro_clp": round(ahorro_clp, 0),
            "porcentaje_reduccion_merma": 65.0
        }

    def format_whatsapp_message(
        self,
        shopping_df: pd.DataFrame,
        restaurant_name: str = "Mi Restaurante",
        periodo_label: str = "Fin de Semana"
    ) -> str:
        """Genera un mensaje de texto formateado listo para enviar a proveedores por WhatsApp."""
        if shopping_df.empty:
            return "No hay insumos proyectados para el período seleccionado."

        lines = [
            f"🛒 *PEDIDO DE COMPRAS - {restaurant_name.upper()}*",
            f"📅 *Período:* {periodo_label}",
            "🛡️ *Cálculo:* Demanda esperada + 15% margen de seguridad",
            "─────────────────────────"
        ]

        for _, row in shopping_df.iterrows():
            insumo = row["insumo"]
            total = row["total_sugerido"]
            unidad = row["unidad"]
            riesgo = row.get("riesgo_caducidad", "MEDIO")
            icono = "🔴" if riesgo == "CRÍTICO" else ("🟠" if riesgo == "ALTO" else "🟢")
            lines.append(f"{icono} *{insumo}*: {total} {unidad}")

        lines.append("─────────────────────────")
        lines.append("🥑 *GastroMerma Chile* | Control inteligente de Food Cost")
        return "\n".join(lines)

    def generate_pdf_report(
        self,
        shopping_df: pd.DataFrame,
        restaurant_name: str = "Restaurante",
        periodo_label: str = "Fin de Semana",
        safety_margin_pct: int = 15,
        waste_metrics: Optional[Dict] = None
    ) -> bytes:
        """Genera un documento PDF formal con la orden de compra sugerida usando ReportLab."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#475569"),
            spaceAfter=12
        )
        alert_style = ParagraphStyle(
            'AlertStyle',
            parent=styles['Normal'],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1E3A8A"),
            spaceAfter=12
        )

        story = []

        # Título y encabezado
        story.append(Paragraph(f"<b>LISTA DE COMPRAS SUGERIDA | {restaurant_name.upper()}</b>", title_style))
        story.append(Paragraph(
            f"<b>Período:</b> {periodo_label} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Margen de Seguridad:</b> +{safety_margin_pct}% &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Generado por:</b> GastroMerma SaaS 🇨🇱",
            subtitle_style
        ))

        if waste_metrics:
            ahorro_str = f"${int(waste_metrics['ahorro_clp']):,}".replace(",", ".")
            story.append(Paragraph(
                f"<b>Prevención de Mermas:</b> Comprar este volumen proyectado previene aprox. "
                f"<b>{waste_metrics['kg_ahorro_merma']} kg</b> de desperdicio por caducidad "
                f"y protege un estimado de <b>{ahorro_str} CLP</b> en Food Cost.",
                alert_style
            ))

        story.append(Spacer(1, 8))

        # Tabla de compras
        table_data = [[
            Paragraph("<b>Insumo Perecible</b>", styles['Normal']),
            Paragraph("<b>Consumo Base</b>", styles['Normal']),
            Paragraph(f"<b>Margen (+{safety_margin_pct}%)</b>", styles['Normal']),
            Paragraph("<b>Total Sugerido</b>", styles['Normal']),
            Paragraph("<b>Unidad</b>", styles['Normal']),
            Paragraph("<b>Riesgo Caducidad</b>", styles['Normal'])
        ]]

        for _, row in shopping_df.iterrows():
            table_data.append([
                Paragraph(str(row["insumo"]), styles['Normal']),
                f"{row['consumo_base']:.2f}",
                f"{row['margen_seguridad']:.2f}",
                f"<b>{row['total_sugerido']:.2f}</b>",
                str(row["unidad"]),
                str(row.get("riesgo_caducidad", "MEDIO"))
            ])

        col_widths = [190, 70, 80, 80, 50, 70]
        report_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        report_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ('ALIGN', (1, 0), (3, -1), 'RIGHT'),
            ('ALIGN', (4, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ]))

        story.append(report_table)
        story.append(Spacer(1, 14))

        # Pie de página
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Italic'],
            fontSize=8,
            textColor=colors.HexColor("#94A3B8"),
            alignment=1
        )
        story.append(Paragraph(
            "Documento generado automáticamente por GastroMerma Chile - Inteligencia de Compras para Restaurantes Independientes.",
            footer_style
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def export_to_excel_bytes(self, shopping_df: pd.DataFrame, periodo_label: str) -> bytes:
        """Exporta la lista de compras sugerida a un archivo Excel (.xlsx) en memoria."""
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            export_df = shopping_df.rename(columns={
                "insumo": "Insumo Perecible",
                "consumo_base": "Consumo Base Estimado",
                "margen_seguridad": "Margen Seguridad (+15%)",
                "total_sugerido": "Total Sugerido Compra",
                "unidad": "Unidad de Compra",
                "riesgo_caducidad": "Nivel de Riesgo Caducidad",
                "platos_asociados": "Platos que lo Utilizan"
            })
            export_df.to_excel(writer, index=False, sheet_name="Lista de Compras")
        output.seek(0)
        return output.getvalue()
