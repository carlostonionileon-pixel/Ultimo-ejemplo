"""Dashboard Streamlit: Cencosud vs Falabella."""

from __future__ import annotations

import logging
from datetime import datetime

import streamlit as st

from src.charts import build_metric_chart
from src.config import COMPANY_NAMES, METRICS
from src.data.yahoo import fetch_all
from src.ui import render_kpi_cards, render_metric_selector, render_sidebar

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="Cencosud vs Falabella",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    period_yf = render_sidebar()

    st.markdown(
        "<h1 style='margin-bottom:4px;'>📊 Cencosud vs Falabella</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#6C757D; margin-top:0;'>Comparación interactiva de precios y fundamentales (últimos 5 años por defecto).</p>",
        unsafe_allow_html=True,
    )

    with st.spinner("Descargando datos de Yahoo Finance..."):
        data = fetch_all(period_yf)

    fundamentals = data.get("fundamentals", {})

    selected_metric_key = render_metric_selector()
    metric = METRICS[selected_metric_key]

    st.divider()
    render_kpi_cards(fundamentals, selected_metric_key)
    st.divider()

    df = fundamentals.get(selected_metric_key)
    if df is None or df.empty or df.dropna(how="all").empty:
        st.warning(
            f"⚠️ Datos no disponibles para **{metric.label}**. "
            "Yahoo Finance no reporta esta métrica para el período seleccionado."
        )
    else:
        title = f"{metric.label}: {COMPANY_NAMES['cencosud']} vs {COMPANY_NAMES['falabella']}"
        fig = build_metric_chart(df, metric, title)
        st.plotly_chart(fig, config={"displayModeBar": True})

    st.divider()
    st.caption(
        f"Datos proporcionados por Yahoo Finance. Última actualización: {datetime.now().strftime('%d-%m-%Y %H:%M')}  "
        "| El rendimiento pasado no garantiza resultados futuros."
    )


if __name__ == "__main__":
    main()
