"""Componentes de UI del dashboard (sidebar, selectores, KPIs)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from src.config import (
    COLORS,
    COMPANY_NAMES,
    DEFAULT_PERIOD,
    METRICS,
    PERIODS,
    MetricConfig,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


def render_sidebar() -> str:
    """Renderiza la barra lateral y retorna el período seleccionado en formato yfinance."""
    with st.sidebar:
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Streamlit_mark_color.svg/512px-Streamlit_mark_color.svg.png",
            width=48,
        )
        st.title("Dashboard Financiero")
        st.markdown("Comparación de **Cencosud** y **Falabella** con datos de Yahoo Finance.")
        st.divider()

        period_label = st.selectbox(
            "Período",
            options=list(PERIODS.keys()),
            index=list(PERIODS.keys()).index(DEFAULT_PERIOD),
        )

        st.divider()
        st.caption("Colores")
        st.markdown(
            f"<span style='color:{COLORS['cencosud']}; font-weight:bold;'>● Cencosud</span> "
            f"<span style='color:{COLORS['falabella']}; font-weight:bold; margin-left:12px;'>● Falabella</span>",
            unsafe_allow_html=True,
        )

        st.divider()
        st.caption("Fuentes")
        st.markdown("- Yahoo Finance  \n- Estados financieros oficiales (fallback)")

        if st.button("🔄 Actualizar datos", width="stretch"):
            st.cache_data.clear()
            st.rerun()

    return PERIODS[period_label]


def render_metric_selector() -> str:
    """Renderiza botones de selección de métrica y retorna la clave seleccionada."""
    st.markdown("### Selecciona la vista")
    labels = [m.short_label for m in METRICS.values()]
    selected_label = st.segmented_control(
        "Métrica",
        options=labels,
        default=labels[0],
        label_visibility="collapsed",
    )
    if selected_label is None:
        selected_label = labels[0]
    for key, cfg in METRICS.items():
        if cfg.short_label == selected_label:
            return key
    return list(METRICS.keys())[0]


def _get_latest_and_prev(df: pd.DataFrame, company: str) -> tuple[float | None, float | None]:
    """Retorna valor más reciente y el anterior disponible para una empresa."""
    if company not in df.columns:
        return None, None
    series = df[company].dropna()
    if series.empty:
        return None, None
    latest = series.iloc[-1]
    prev = series.iloc[-2] if len(series) > 1 else None
    return latest, prev


def _compute_delta(latest: float | None, prev: float | None) -> float | None:
    if latest is None or prev is None or prev == 0:
        return None
    return latest - prev


def _format_value(value: float | None, metric: MetricConfig) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "N/A"
    return metric.formatter(value)


def render_kpi_cards(fundamentals: dict[str, pd.DataFrame], selected_metric_key: str) -> None:
    """Renderiza tarjetas KPI para la métrica seleccionada."""
    metric = METRICS[selected_metric_key]
    df = fundamentals.get(selected_metric_key, pd.DataFrame())

    cols = st.columns(2)
    for idx, company in enumerate(["cencosud", "falabella"]):
        latest, prev = _get_latest_and_prev(df, company)
        value_str = _format_value(latest, metric)
        delta = _compute_delta(latest, prev)
        delta_html = ""
        if delta is not None and latest is not None and prev is not None:
            delta_str = metric.formatter(delta)
            # Determina color según si es positivo o negativo
            is_positive = delta >= 0
            delta_color = "#28A745" if is_positive else "#DC3545"
            arrow = "▲" if is_positive else "▼"
            delta_html = f"""
                <p style="margin:8px 0 0 0; font-size:14px; color:{delta_color}; font-weight:600;">
                    {arrow} {delta_str} vs anterior
                </p>
            """

        with cols[idx]:
            st.markdown(
                f"""
                <div style="
                    background-color: white;
                    border-left: 6px solid {COLORS[company]};
                    border-radius: 8px;
                    padding: 16px;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
                ">
                    <p style="margin:0; color:#6C757D; font-size:13px;">{COMPANY_NAMES[company]}</p>
                    <p style="margin:4px 0 0 0; font-size:28px; font-weight:700; color:#212529;">{value_str}</p>
                    <p style="margin:4px 0 0 0; font-size:13px; color:#ADB5BD;">{metric.label}</p>
                    {delta_html}
                </div>
                """,
                unsafe_allow_html=True,
            )
