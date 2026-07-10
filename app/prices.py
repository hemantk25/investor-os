from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Quote:
    price: float
    day_pct: float | None


_cache: dict = {}


def _frame_to_quotes(df, symbols) -> dict[str, Quote]:
    out = {}
    close = df["Close"] if "Close" in df.columns.get_level_values(0) else df
    for s in symbols:
        col = f"{s}.NS"
        if col not in close.columns:
            continue
        series = close[col].dropna()
        if series.empty:
            continue
        price = float(series.iloc[-1])
        day = float((series.iloc[-1] / series.iloc[-2] - 1) * 100) if len(series) >= 2 else None
        out[s] = Quote(price=price, day_pct=day)
    return out


def _series_from_frame(df, symbol: str):
    if df is None or getattr(df, "empty", True):
        return None
    columns = getattr(df, "columns", None)
    if columns is None:
        return None
    try:
        levels = columns.nlevels
    except Exception:
        levels = 1
    if levels > 1:
        try:
            if "Close" in columns.get_level_values(0):
                close = df["Close"]
                if symbol in close.columns:
                    return close[symbol].dropna()
        except Exception:
            pass
        try:
            if symbol in columns.get_level_values(0) and "Close" in df[symbol].columns:
                return df[symbol]["Close"].dropna()
        except Exception:
            pass
        return None
    if "Close" in columns:
        return df["Close"].dropna()
    if symbol in columns:
        return df[symbol].dropna()
    return None


def _generic_frame_to_quotes(df, symbols) -> dict[str, Quote]:
    out = {}
    for symbol in symbols:
        series = _series_from_frame(df, symbol)
        if series is None or series.empty:
            continue
        price = float(series.iloc[-1])
        day = float((series.iloc[-1] / series.iloc[-2] - 1) * 100) if len(series) >= 2 else None
        out[symbol] = Quote(price=price, day_pct=day)
    return out


def fetch_quotes(nse_symbols: list[str], ttl: int = 300) -> dict[str, Quote]:
    symbols = sorted(set(s for s in nse_symbols if s))
    if not symbols:
        return {}
    key = tuple(symbols)
    now = time.time()
    if key in _cache and now - _cache[key][0] < ttl:
        return _cache[key][1]
    try:
        import yfinance as yf
        df = yf.download([f"{s}.NS" for s in symbols], period="5d", interval="1d",
                         progress=False, threads=True, group_by="column")
        quotes = _frame_to_quotes(df, symbols)
    except Exception:
        quotes = {}
    if quotes:
        _cache[key] = (now, quotes)
    return quotes


def fetch_market_quotes(symbols: list[str], ttl: int = 300) -> dict[str, Quote]:
    symbols = sorted(set(s for s in symbols if s))
    if not symbols:
        return {}
    key = ("market", tuple(symbols))
    now = time.time()
    if key in _cache and now - _cache[key][0] < ttl:
        return _cache[key][1]
    try:
        import yfinance as yf
        df = yf.download(symbols, period="5d", interval="1d", progress=False,
                         threads=True, group_by="column")
        quotes = _generic_frame_to_quotes(df, symbols)
    except Exception:
        quotes = {}
    if quotes:
        _cache[key] = (now, quotes)
    return quotes


def _history_from_frame(df, symbols) -> dict:
    out = {}
    close = df["Close"] if "Close" in getattr(df.columns, "get_level_values", lambda _: [])(0) else df
    for s in symbols:
        col = f"{s}.NS"
        if col in close.columns:
            series = close[col].dropna().tolist()
            if series:
                out[s] = [float(x) for x in series]
    return out


_hist_cache: dict = {}


def fetch_history(nse_symbols: list[str], period: str = "6mo", ttl: int = 3600) -> dict:
    symbols = sorted(set(s for s in nse_symbols if s))
    if not symbols:
        return {}
    key = (period, tuple(symbols))
    now = time.time()
    if key in _hist_cache and now - _hist_cache[key][0] < ttl:
        return _hist_cache[key][1]
    try:
        import yfinance as yf
        df = yf.download([f"{s}.NS" for s in symbols], period=period, interval="1d",
                         progress=False, threads=True, group_by="column")
        hist = _history_from_frame(df, symbols)
    except Exception:
        hist = {}
    if hist:
        _hist_cache[key] = (now, hist)
    return hist
