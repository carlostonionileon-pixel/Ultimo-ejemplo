"""Constructores de gráficos Plotly con estilo Power BI."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import COLORS, COMPANY_NAMES, MetricConfig

if TYPE_CHECKING:
    from plotly.graph_objects import Figure


# Paleta Power BI-like
TEMPLATE = {
    "layout": {
        "font": {"family": "Segoe UI, Roboto, Helvetica, Arial, sans-serif", "size": 13},
        "paper_bgcolor": "white",
        "plot_bgcolor": "#F8F9FA",
        "margin": {"l": 60, "r": 40, "t": 80, "b": 60},
        "hovermode": "x unified",
        "xaxis": {
            "showgrid": True,
            "gridcolor": "#E9ECEF",
            "gridwidth": 1,
            "linecolor": "#ADB5BD",
            "tickfont": {"color": "#495057"},
        },
        "yaxis": {
            "showgrid": True,
            "gridcolor": "#E9ECEF",
            "gridwidth": 1,
            "linecolor": "#ADB5BD",
            "tickfont": {"color": "#495057"},
        },
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "bgcolor": "rgba(255,255,255,0.8)",
        },
    }
}


def _format_hover(value: float | None, metric: MetricConfig) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "N/A"
    return metric.formatter(value)


def build_metric_chart(
    df: pd.DataFrame,
    metric: MetricConfig,
    title: str,
) -> Figure:
    """Crea un gráfico interactivo para la métrica seleccionada.

    Param df: DataFrame con columnas ['cencosud', 'falabella'] e índice de fechas.
    """
    fig = make_subplots(rows=1, cols=1)

    sparse_metrics = {"net_income", "net_margin"}
    mode = "lines+markers" if metric.key in sparse_metrics else "lines"
    marker_size = 10 if metric.key in sparse_metrics else 0

    for company in ["cencosud", "falabella"]:
        if company not in df.columns:
            continue
        series = df[company].dropna()
        if series.empty:
            continue

        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series.values,
                mode=mode,
                name=COMPANY_NAMES[company],
                line={"color": COLORS[company], "width": 3},
                marker={"size": marker_size, "color": COLORS[company], "line": {"width": 2, "color": "white"}},
                hovertemplate=(
                    f"<b>{COMPANY_NAMES[company]}</b><br>"
                    "Fecha: %{x|%d-%m-%Y}<br>"
                    f"{metric.short_label}: %{{customdata}}<extra></extra>"
                ),
                customdata=[_format_hover(v, metric) for v in series.values],
            )
        )

    fig.update_layout(
        title={
            "text": f"<b>{title}</b>",
            "font": {"size": 20, "color": "#212529"},
            "x": 0.0,
            "xanchor": "left",
        },
        xaxis_title="Tiempo",
        yaxis_title=metric.y_title,
        template=TEMPLATE,
        height=520,
    )

    # Rangeselector tipo Power BI
    fig.update_xaxes(
        rangeslider_visible=False,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="1A", step="year", stepmode="backward"),
                dict(count=5, label="5A", step="year", stepmode="backward"),
                dict(step="all", label="Todo"),
            ]),
            bgcolor="#F8F9FA",
            activecolor=COLORS["cencosud"],
        ),
    )

    return fig
