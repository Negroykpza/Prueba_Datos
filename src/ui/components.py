"""Componentes visuales reutilizables, tarjetas de métricas y estilos para Streamlit."""

import streamlit as st


def inject_custom_styles():
    """Inyecta estilos CSS para una apariencia gastronómica profesional y moderna."""
    st.markdown("""
        <style>
        /* Estilos generales */
        .main-header {
            font-size: 2.1rem;
            font-weight: 700;
            color: #1E293B;
            margin-bottom: 0.2rem;
        }
        .sub-header {
            font-size: 1.05rem;
            color: #64748B;
            margin-bottom: 1.5rem;
        }
        .metric-card {
            background: linear-gradient(135deg, #F8FAFC 0%, #FFFFFF 100%);
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 16px 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 12px;
        }
        .metric-title {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748B;
            font-weight: 600;
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #0F172A;
            margin-top: 4px;
        }
        .metric-caption {
            font-size: 0.8rem;
            color: #10B981;
            margin-top: 2px;
        }
        .banner-tip {
            background-color: #EFF6FF;
            border-left: 4px solid #3B82F6;
            padding: 12px 16px;
            border-radius: 6px;
            color: #1E40AF;
            font-size: 0.92rem;
            margin-bottom: 16px;
        }
        .badge-success {
            background-color: #D1FAE5;
            color: #065F46;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .badge-warning {
            background-color: #FEF3C7;
            color: #92400E;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)


def render_metric_card(title: str, value: str, caption: str = "", delta_color: str = "#10B981"):
    """Renderiza una tarjeta de KPI estilizada."""
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            {f'<div class="metric-caption" style="color:{delta_color};">{caption}</div>' if caption else ''}
        </div>
    """, unsafe_allow_html=True)


def render_info_banner(title: str, message: str):
    """Renderiza un banner informativo tipo recomendación culinaria."""
    st.markdown(f"""
        <div class="banner-tip">
            <strong>{title}</strong><br>{message}
        </div>
    """, unsafe_allow_html=True)


def render_financial_hero_card(
    title: str,
    value: str,
    caption: str,
    badge: str = "",
    theme: str = "green"
):
    """Renderiza tarjetas financieras destacadas con contraste alto (verde ahorro, rojo fuga, azul food cost)."""
    themes = {
        "green": {
            "bg": "linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%)",
            "border": "#10B981",
            "title_color": "#065F46",
            "val_color": "#047857",
            "badge_bg": "#A7F3D0",
            "badge_color": "#064E3B",
            "caption_color": "#047857"
        },
        "red": {
            "bg": "linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%)",
            "border": "#EF4444",
            "title_color": "#991B1B",
            "val_color": "#B91C1C",
            "badge_bg": "#FECACA",
            "badge_color": "#7F1D1D",
            "caption_color": "#B91C1C"
        },
        "blue": {
            "bg": "linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%)",
            "border": "#3B82F6",
            "title_color": "#1E40AF",
            "val_color": "#1D4ED8",
            "badge_bg": "#BFDBFE",
            "badge_color": "#1E3A8A",
            "caption_color": "#1E40AF"
        }
    }
    t = themes.get(theme, themes["green"])
    badge_html = f'<span style="background:{t["badge_bg"]}; color:{t["badge_color"]}; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; letter-spacing:0.04em;">{badge}</span>' if badge else ""

    st.markdown(f"""
        <div style="background:{t['bg']}; border:2px solid {t['border']}; border-radius:12px; padding:18px 20px; box-shadow:0 2px 6px rgba(0,0,0,0.05); margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <span style="font-size:0.82rem; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; color:{t['title_color']};">{title}</span>
                {badge_html}
            </div>
            <div style="font-size:2.0rem; font-weight:800; color:{t['val_color']}; line-height:1.2; margin-bottom:6px;">{value}</div>
            <div style="font-size:0.83rem; color:{t['caption_color']}; font-weight:500;">{caption}</div>
        </div>
    """, unsafe_allow_html=True)

