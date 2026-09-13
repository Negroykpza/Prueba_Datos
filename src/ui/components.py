"""Componentes visuales reutilizables, tarjetas de métricas en Dark Mode nativo y estilos para EZtock."""

import streamlit as st


def inject_custom_styles():
    """Inyecta estilos CSS para una apariencia gastronómica profesional, moderna y native Dark Mode."""
    st.markdown("""
        <style>
        /* =====================================================================
           ESTILOS GLOBALES Y TIPOGRAFÍA
           ===================================================================== */
        .main-header {
            font-size: 2.15rem;
            font-weight: 800;
            color: #F8FAFC !important;
            letter-spacing: -0.02em;
            margin-bottom: 0.25rem;
        }
        .sub-header {
            font-size: 1.02rem;
            color: #94A3B8 !important;
            margin-bottom: 1.5rem;
            line-height: 1.5;
        }

        /* =====================================================================
           TARJETAS DE MÉTRICAS (KPIS) - MODO OSCURO NATIVO ELEVADO
           ===================================================================== */
        .metric-card-container {
            background-color: #1E293B;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 16px 18px;
            min-height: 125px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -2px rgba(0, 0, 0, 0.15);
            transition: transform 0.15s ease, border-color 0.15s ease;
            margin-bottom: 14px;
        }
        .metric-card-container:hover {
            border-color: #475569;
            transform: translateY(-2px);
        }
        .metric-header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }
        .metric-title-text {
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #94A3B8 !important;
        }
        .metric-value-text {
            font-size: 1.75rem;
            font-weight: 800;
            color: #F8FAFC !important;
            line-height: 1.2;
            letter-spacing: -0.01em;
        }
        .metric-caption-text {
            font-size: 0.8rem;
            color: #64748B !important;
            margin-top: 4px;
        }

        /* Pills y Deltas */
        .delta-pill {
            font-size: 0.72rem;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 9999px;
            display: inline-flex;
            align-items: center;
        }
        .delta-positive {
            background-color: rgba(16, 185, 129, 0.15);
            color: #34D399 !important;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .delta-warning {
            background-color: rgba(245, 158, 11, 0.15);
            color: #FBBF24 !important;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }
        .delta-neutral {
            background-color: rgba(148, 163, 184, 0.15);
            color: #CBD5E1 !important;
            border: 1px solid rgba(148, 163, 184, 0.25);
        }
        .delta-negative {
            background-color: rgba(239, 68, 68, 0.15);
            color: #F87171 !important;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        /* =====================================================================
           TARJETAS DE HÉROE FINANCIERO ($ CLP)
           ===================================================================== */
        .financial-hero-card {
            background-color: #1E293B;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 18px 20px;
            margin-bottom: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            position: relative;
            overflow: hidden;
        }
        .financial-hero-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .financial-hero-title {
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94A3B8;
        }
        .financial-hero-value {
            font-size: 1.95rem;
            font-weight: 800;
            line-height: 1.2;
        }
        .financial-hero-caption {
            font-size: 0.82rem;
            color: #CBD5E1;
            margin-top: 6px;
        }

        /* =====================================================================
           ALERTAS OPERATIVAS (FRENA COMPRAS Y PROMOCIÓN PREVENTIVA)
           ===================================================================== */
        .alert-card-dark {
            background-color: #1E293B;
            border-radius: 10px;
            padding: 16px 18px;
            margin-bottom: 14px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        }
        .alert-card-danger {
            border: 1px solid #991B1B;
            border-left: 5px solid #EF4444;
        }
        .alert-card-warning {
            border: 1px solid #92400E;
            border-left: 5px solid #F59E0B;
        }
        .alert-item-box {
            background: rgba(15, 23, 42, 0.6);
            border-radius: 6px;
            padding: 10px 12px;
            margin-bottom: 8px;
            border: 1px solid #334155;
        }

        /* =====================================================================
           BARRA LATERAL (SIDEBAR) DE ALTO CONTRASTE
           ===================================================================== */
        .sidebar-section-title {
            font-size: 0.85rem;
            font-weight: 700;
            color: #F8FAFC !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 14px;
            margin-bottom: 6px;
        }
        .sidebar-info-box {
            background-color: #1E293B;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px 14px;
            font-size: 0.84rem;
            color: #CBD5E1 !important;
            line-height: 1.6;
        }
        .sidebar-info-box strong {
            color: #F8FAFC !important;
        }
        .sidebar-highlight {
            color: #38BDF8 !important;
            font-weight: 700;
        }

        /* =====================================================================
           EXPLORADOR DE DATOS Y BANNERS
           ===================================================================== */
        .data-inspect-card {
            background-color: #1E293B;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 16px 20px;
            margin-top: 12px;
            margin-bottom: 12px;
        }
        .data-inspect-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .banner-tip-dark {
            background-color: #1E293B;
            border-left: 4px solid #38BDF8;
            border-top: 1px solid #334155;
            border-right: 1px solid #334155;
            border-bottom: 1px solid #334155;
            padding: 14px 18px;
            border-radius: 8px;
            color: #E2E8F0 !important;
            font-size: 0.92rem;
            margin-bottom: 18px;
            line-height: 1.5;
        }
        .banner-tip-dark strong {
            color: #38BDF8 !important;
        }

        /* =====================================================================
           LLAMADO A LA ACCIÓN (CTA BUTTONS)
           ===================================================================== */
        .cta-container {
            margin-top: 24px;
            margin-bottom: 24px;
            padding-top: 16px;
            border-top: 1px solid #334155;
        }

        /* Estilo para selector horizontal de navegación superior */
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            gap: 8px;
            background-color: #0F172A;
            padding: 6px;
            border-radius: 10px;
            border: 1px solid #334155;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] > label {
            background-color: #1E293B;
            border: 1px solid #334155;
            padding: 8px 16px;
            border-radius: 8px;
            color: #CBD5E1;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] {
            background-color: #2563EB !important;
            color: #FFFFFF !important;
            border-color: #3B82F6 !important;
        }
        </style>
    """, unsafe_allow_html=True)


def render_metric_card(
    title: str,
    value: str,
    caption: str = "",
    delta: str = "",
    delta_type: str = "neutral"
):
    """
    Renderiza una tarjeta de KPI native Dark Mode con contenedor elevado,
    tipografía de alta legibilidad y badge de variación opcional.
    """
    delta_class = "delta-neutral"
    if delta_type == "positive":
        delta_class = "delta-positive"
    elif delta_type == "warning":
        delta_class = "delta-warning"
    elif delta_type == "negative":
        delta_class = "delta-negative"

    delta_html = f'<span class="delta-pill {delta_class}">{delta}</span>' if delta else ""
    caption_html = f'<div class="metric-caption-text">{caption}</div>' if caption else ""

    st.markdown(f"""
        <div class="metric-card-container">
            <div class="metric-header-row">
                <span class="metric-title-text">{title}</span>
                {delta_html}
            </div>
            <div class="metric-value-text">{value}</div>
            {caption_html}
        </div>
    """, unsafe_allow_html=True)


def render_financial_hero_card(
    title: str,
    value: str,
    caption: str,
    accent_color: str = "#10B981",
    badge_text: str = ""
):
    """Renderiza una tarjeta héroe financiero en Dark Mode con énfasis visual."""
    badge_html = f'<span class="delta-pill delta-positive" style="color: {accent_color}; border-color: {accent_color}55;">{badge_text}</span>' if badge_text else ""
    st.markdown(f"""
        <div class="financial-hero-card" style="border-top: 3px solid {accent_color};">
            <div class="financial-hero-top">
                <span class="financial-hero-title">{title}</span>
                {badge_html}
            </div>
            <div class="financial-hero-value" style="color: {accent_color};">{value}</div>
            <div class="financial-hero-caption">{caption}</div>
        </div>
    """, unsafe_allow_html=True)


def render_info_banner(title: str, message: str):
    """Renderiza un banner informativo tipo recomendación culinaria en Dark Mode."""
    st.markdown(f"""
        <div class="banner-tip-dark">
            <strong>{title}</strong><br>{message}
        </div>
    """, unsafe_allow_html=True)
