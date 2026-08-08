"""Configuración central del dashboard: tickers, colores, métricas y períodos."""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class MetricConfig:
    key: str
    label: str
    short_label: str
    unit: str
    formatter: Callable[[float], str]
    y_title: str


TICKERS = {
    "cencosud": "CENCOSUD.SN",
    "falabella": "FALABELLA.SN",
}

COMPANY_NAMES = {
    "cencosud": "Cencosud",
    "falabella": "Falabella",
}

COLORS = {
    "cencosud": "#00A3E0",  # celeste
    "falabella": "#00843D",  # verde
}

PERIODS = {
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1A": "1y",
    "5A": "5y",
    "Máx": "max",
}

DEFAULT_PERIOD = "5A"


def _clp_billions(value: float) -> str:
    """Miles de millones de CLP (1e9)."""
    if value is None or (isinstance(value, float) and value != value):  # NaN
        return "N/A"
    return f"${value/1e9:,.1f} mil millones"


def _clp_millions(value: float) -> str:
    """Millones de CLP (1e6)."""
    if value is None or (isinstance(value, float) and value != value):
        return "N/A"
    return f"${value/1e6:,.0f} millones"


def _percent(value: float) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "N/A"
    return f"{value*100:,.1f}%"


def _ratio(value: float) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "N/A"
    return f"{value:,.2f}x"


def _clp(value: float) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "N/A"
    return f"${value:,.0f}"


METRICS: dict[str, MetricConfig] = {
    "price": MetricConfig(
        key="price",
        label="Precio Ajustado",
        short_label="Precio",
        unit="CLP",
        formatter=_clp,
        y_title="Precio (CLP)",
    ),
    "pe": MetricConfig(
        key="pe",
        label="Relación Precio/Utilidad (P/E)",
        short_label="P/E",
        unit="x",
        formatter=_ratio,
        y_title="P/E (x)",
    ),
    "market_cap": MetricConfig(
        key="market_cap",
        label="Capitalización de Mercado",
        short_label="Market Cap",
        unit="CLP",
        formatter=_clp_billions,
        y_title="Capitalización (miles de millones CLP)",
    ),
    "net_income": MetricConfig(
        key="net_income",
        label="Utilidad Neta",
        short_label="Utilidad Neta",
        unit="CLP",
        formatter=_clp_billions,
        y_title="Utilidad Neta (miles de millones CLP)",
    ),
    "net_margin": MetricConfig(
        key="net_margin",
        label="Margen de Utilidad Neta",
        short_label="Margen Neto",
        unit="%",
        formatter=_percent,
        y_title="Margen Neto (%)",
    ),
    "dividend_yield": MetricConfig(
        key="dividend_yield",
        label="Dividendo Yield",
        short_label="Div. Yield",
        unit="%",
        formatter=_percent,
        y_title="Dividendo Yield (%)",
    ),
}
