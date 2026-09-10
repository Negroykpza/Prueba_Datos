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
