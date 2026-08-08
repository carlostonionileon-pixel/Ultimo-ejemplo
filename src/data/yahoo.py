"""Fetchers de datos de Yahoo Finance para Cencosud y Falabella."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from src.config import TICKERS

logger = logging.getLogger(__name__)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_history(tickers: dict[str, str], period_yf: str) -> dict[str, pd.DataFrame]:
    """Obtiene historial de precios y dividendos para cada ticker.

    Retorna dict {company: DataFrame(index=fecha, columns=['Close', 'Dividends'])}.
    """
    result: dict[str, pd.DataFrame] = {}
    for company, ticker in tickers.items():
        try:
            history = yf.Ticker(ticker).history(period=period_yf, auto_adjust=True)
            if history.empty:
                logger.warning("No hay datos de precios para %s (%s)", company, ticker)
                continue
            history.index = pd.to_datetime(history.index).tz_localize(None)
            result[company] = history[["Close", "Dividends"]].copy()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error descargando precios de %s: %s", ticker, exc)
    return result


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_info(tickers: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Obtiene métricas de información del ticker.

    Retorna dict anidado: {company: {sharesOutstanding, marketCap, trailingPE, dividendYield}}.
    """
    result: dict[str, dict[str, Any]] = {}
    for company, ticker in tickers.items():
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error obteniendo info de %s: %s", ticker, exc)
            info = {}

        result[company] = {
            "shares_outstanding": info.get("sharesOutstanding"),
            "market_cap": info.get("marketCap"),
            "trailing_pe": info.get("trailingPE") or info.get("forwardPE"),
            "dividend_yield": info.get("dividendYield"),
        }
    return result


def _extract_from_financial_table(
    financials: pd.DataFrame | None,
    company_data: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Extrae ingresos, utilidad neta y EPS desde un DataFrame de estados financieros."""
    if financials is None or financials.empty:
        return company_data

    fin = financials.T
    for col in fin.columns:
        lowered = str(col).lower()
        if "total revenue" in lowered or "totalrevenue" in lowered:
            company_data["revenue"]["value"] = fin[col]
        if col == "Net Income" or lowered == "net income":
            company_data["net_income"]["value"] = fin[col]
        if col == "Diluted EPS" or lowered == "diluted eps":
            company_data["eps"]["value"] = fin[col]
        elif company_data["eps"].empty and (col == "Basic EPS" or lowered == "basic eps"):
            company_data["eps"]["value"] = fin[col]
    return company_data


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_financials(tickers: dict[str, str]) -> dict[str, dict[str, pd.DataFrame]]:
    """Obtiene estados financieros anuales, con fallback a trimestrales.

    Retorna {company: {'revenue': df, 'net_income': df, 'eps': df}} donde el índice es fecha.
    """
    result: dict[str, dict[str, pd.DataFrame]] = {}
    for company, ticker in tickers.items():
        company_data: dict[str, pd.DataFrame] = {
            "revenue": pd.DataFrame(),
            "net_income": pd.DataFrame(),
            "eps": pd.DataFrame(),
        }
        try:
            ticker_obj = yf.Ticker(ticker)
            financials = ticker_obj.financials
            if financials is None or financials.empty:
                logger.info("Usando quarterly_financials como fallback para %s", ticker)
                financials = ticker_obj.quarterly_financials
            company_data = _extract_from_financial_table(financials, company_data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error obteniendo financials de %s: %s", ticker, exc)

        result[company] = company_data
    return result


def _normalize_dividend_yield(value: Any) -> float | None:
    """Normaliza dividendYield de yfinance a decimal."""
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value != value:  # NaN
        return None
    # yfinance a veces devuelve 1.25 en lugar de 0.0125 para acciones chilenas
    if value > 1:
        return value / 100.0
    return value


import numpy as np


def _rolling_dividend_yield(prices: pd.Series, dividends: pd.Series) -> pd.Series:
    """Calcula dividend yield trailing 12 meses para cada día."""
    divs = dividends.dropna()
    divs = divs[divs > 0]
    if divs.empty or prices.empty:
        return pd.Series(index=prices.index, dtype=float)

    results = []
    for date, price in prices.items():
        if pd.isna(price) or price == 0:
            results.append(np.nan)
            continue
        start = date - pd.DateOffset(months=12)
        ttm_div = divs[(divs.index > start) & (divs.index <= date)].sum()
        results.append(ttm_div / price)
    return pd.Series(results, index=prices.index, dtype=float)


def _compute_pe_series(prices: pd.Series, eps_series: pd.Series) -> pd.Series:
    """Calcula P/E diario usando el EPS anual más reciente disponible."""
    if eps_series.empty or prices.empty:
        return pd.Series(index=prices.index, dtype=float)

    eps_series = eps_series.dropna().sort_index()
    pe_values = []
    for date, price in prices.items():
        # EPS más reciente hasta la fecha
        available = eps_series[eps_series.index <= date]
        if available.empty or price == 0 or pd.isna(price):
            pe_values.append(np.nan)
            continue
        eps = available.iloc[-1]
        if eps == 0 or pd.isna(eps):
            pe_values.append(np.nan)
        else:
            pe_values.append(price / eps)
    return pd.Series(pe_values, index=prices.index, dtype=float)


def build_fundamental_series(
    history: dict[str, pd.DataFrame],
    info: dict[str, dict[str, Any]],
    financials: dict[str, dict[str, pd.DataFrame]],
) -> dict[str, pd.DataFrame]:
    """Construye series temporales de métricas fundamentales.

    Retorna dict {metric: DataFrame(index=fecha, columns=[cencosud, falabella])}.
    Métricas: price, pe, market_cap, dividend_yield, net_income, net_margin.
    """
    companies = list(TICKERS.keys())
    series: dict[str, pd.DataFrame] = {}

    # Precios
    price_by_company: dict[str, pd.Series] = {}
    for company in companies:
        hist = history.get(company)
        if hist is not None and not hist.empty and "Close" in hist.columns:
            price_by_company[company] = hist["Close"]
    if price_by_company:
        series["price"] = pd.concat(price_by_company, axis=1).sort_index()

    # P/E diario calculado desde precio y EPS anual
    pe_by_company: dict[str, pd.Series] = {}
    for company in companies:
        prices = price_by_company.get(company)
        eps_df = financials.get(company, {}).get("eps", pd.DataFrame())
        if prices is not None and not eps_df.empty and "value" in eps_df.columns:
            pe_by_company[company] = _compute_pe_series(prices, eps_df["value"])
    if pe_by_company:
        series["pe"] = pd.concat(pe_by_company, axis=1).sort_index()

    # Market cap diario calculado desde precio * acciones en circulación
    market_cap_by_company: dict[str, pd.Series] = {}
    for company in companies:
        prices = price_by_company.get(company)
        shares = info.get(company, {}).get("shares_outstanding")
        if prices is not None and shares:
            market_cap_by_company[company] = prices * float(shares)
    if market_cap_by_company:
        series["market_cap"] = pd.concat(market_cap_by_company, axis=1).sort_index()

    # Dividendo yield trailing 12 meses
    div_yield_by_company: dict[str, pd.Series] = {}
    for company in companies:
        hist = history.get(company)
        if hist is not None and not hist.empty:
            div_yield_by_company[company] = _rolling_dividend_yield(hist["Close"], hist["Dividends"])
    if div_yield_by_company:
        series["dividend_yield"] = pd.concat(div_yield_by_company, axis=1).sort_index()

    # Utilidad neta e ingresos desde financials (puntos anuales)
    revenue_by_company: dict[str, pd.Series] = {}
    net_income_by_company: dict[str, pd.Series] = {}
    for company in companies:
        rev_df = financials.get(company, {}).get("revenue", pd.DataFrame())
        inc_df = financials.get(company, {}).get("net_income", pd.DataFrame())
        if not rev_df.empty and "value" in rev_df.columns:
            revenue_by_company[company] = rev_df["value"].dropna()
        if not inc_df.empty and "value" in inc_df.columns:
            net_income_by_company[company] = inc_df["value"].dropna()

    if net_income_by_company:
        series["net_income"] = pd.concat(net_income_by_company, axis=1).sort_index()

    # Margen neto anual
    if revenue_by_company and net_income_by_company:
        rev = pd.concat(revenue_by_company, axis=1)
        inc = pd.concat(net_income_by_company, axis=1)
        common = rev.index.intersection(inc.index)
        if not common.empty:
            margin = (inc.loc[common] / rev.loc[common]).dropna(how="all")
            series["net_margin"] = margin

    return series


def fetch_all(period_yf: str) -> dict[str, Any]:
    """Orquesta la descarga de precios, info y fundamentales.

    Retorna dict con:
      - prices: DataFrame
      - info: dict
      - financials: dict
      - fundamentals: dict de series temporales
    """
    history = fetch_history(TICKERS, period_yf)
    info = fetch_info(TICKERS)
    financials = fetch_financials(TICKERS)
    fundamentals = build_fundamental_series(history, info, financials)
    return {
        "prices": fundamentals.get("price", pd.DataFrame()),
        "info": info,
        "financials": financials,
        "fundamentals": fundamentals,
    }
