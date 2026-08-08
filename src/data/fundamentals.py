"""Fallback para estados financieros cuando Yahoo Finance no tiene datos.

Este módulo intenta obtener datos fundamentales desde fuentes oficiales si yfinance
falla. Es un fallback defensivo: si no puede parsear la fuente, retorna DataFrames
vacíos y la app muestra "Datos no disponibles".
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

IR_URLS: dict[str, str] = {
    "cencosud": "https://www.cencosud.com/inversionistas/estados-financieros/",
    "falabella": "https://www.falabella.com/falabella-cl/page/inversionistas",
}


def _parse_number(text: str | None) -> float | None:
    """Limpia un string con número chileno/estadounidense y lo convierte a float."""
    if not text:
        return None
    cleaned = text.replace("$", "").replace("%", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def scrape_ir_page(company: str) -> dict[str, pd.DataFrame]:
    """Intenta extraer tablas de estados financieros de la página de IR oficial.

    Por lo general estas páginas usan PDF/Excel o renderizan con JavaScript, por lo
    que este scraper es un fallback de último recurso. Retorna dict vacío si falla.
    """
    url = IR_URLS.get(company)
    if not url:
        return {"revenue": pd.DataFrame(), "net_income": pd.DataFrame(), "eps": pd.DataFrame()}

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; FinanceDashboard/1.0)"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Buscar tablas HTML con palabras clave
        tables = soup.find_all("table")
        for table in tables:
            text = table.get_text(separator=" ", strip=True).lower()
            if any(k in text for k in ["ingresos", "utilidad", "resultado", "revenue", "net income"]):
                df = pd.read_html(str(table))[0]
                logger.info("Tabla candidata encontrada en %s con %s filas", url, len(df))
                # Sin un formato estable no intentamos mapear columnas; registramos para extensión futura.
                break
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo scrapear IR de %s: %s", company, exc)

    return {"revenue": pd.DataFrame(), "net_income": pd.DataFrame(), "eps": pd.DataFrame()}


def fallback_financials(ticker_symbol: str, company: str) -> dict[str, pd.DataFrame]:
    """Punto de entrada del fallback.

    Retorna estructura compatible con fetch_financials de yahoo.py.
    """
    logger.info("Activando fallback financiero para %s (%s)", company, ticker_symbol)
    return scrape_ir_page(company)


def merge_with_fallback(
    yahoo_financials: dict[str, dict[str, pd.DataFrame]],
) -> dict[str, dict[str, pd.DataFrame]]:
    """Rellena métricas faltantes de yfinance con el fallback de IR."""
    result: dict[str, dict[str, pd.DataFrame]] = {}
    # Mapping inverso de ticker -> company
    from src.config import TICKERS

    company_by_ticker = {v: k for k, v in TICKERS.items()}

    for ticker, data in yahoo_financials.items():
        company = company_by_ticker.get(ticker, ticker)
        merged = {"revenue": data["revenue"], "net_income": data["net_income"], "eps": data["eps"]}
        needs_fallback = any(df.empty for df in merged.values())
        if needs_fallback:
            fallback = fallback_financials(ticker, company)
            for key in merged:
                if merged[key].empty and not fallback[key].empty:
                    merged[key] = fallback[key]
        result[ticker] = merged

    return result
