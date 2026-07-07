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
