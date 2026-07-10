from __future__ import annotations

import hashlib
import socket
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import feedparser

from app import storage


MARKETS = ["India", "US", "UAE", "Canada", "Global"]

MARKET_FEED_CAP = 25
HOLDING_FEED_CAP = 10
TOP_HOLDINGS_CAP = 40
PRUNE_KEEP = 500
PRUNE_AFTER_DAYS = 14
FEED_TIMEOUT_SECS = 10

LOCALES = {"India": ("en-IN", "IN", "IN:en"), "US": ("en-US", "US", "US:en"),
           "UAE": ("en-AE", "AE", "AE:en"), "Canada": ("en-CA", "CA", "CA:en"),
           "Global": ("en-US", "US", "US:en")}
QUERIES = {"India": "Nifty OR Sensex OR Indian stock market",
           "US": "US stock market OR S&P 500 OR Nasdaq",
           "UAE": "UAE stocks OR DFM OR ADX", "Canada": "TSX OR Canadian stock market",
           "Global": "global markets"}


def market_feed_url(market: str) -> str:
    hl, gl, ceid = LOCALES[market]
    return ("https://news.google.com/rss/search?q=" + quote_plus(QUERIES[market])
            + f"&hl={hl}&gl={gl}&ceid={quote_plus(ceid)}")


def holding_feed_url(name: str) -> str:
    return ("https://news.google.com/rss/search?q=" + quote_plus(f'"{name}" NSE')
            + "&hl=en-IN&gl=IN&ceid=" + quote_plus("IN:en"))


def _url_hash(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()


def _safe_url(url: str) -> bool:
    # Feed data is untrusted input; only plain web links may reach an href.
    try:
        return urlparse(url).scheme in ("http", "https")
    except ValueError:
        return False


def normalize_entries(parsed, market: str, isin: str | None, holding_name: str | None) -> list[dict]:
    cap = HOLDING_FEED_CAP if (isin or holding_name) else MARKET_FEED_CAP
    out = []
    for entry in getattr(parsed, "entries", [])[:cap]:
        title = entry.get("title") or ""
        url = entry.get("link") or ""
        if not title or not url or not _safe_url(url):
            continue
        source = entry.get("source") or {}
        publisher = source.get("title") if isinstance(source, dict) else None
        pp = entry.get("published_parsed")
        published_at = datetime(*pp[:6]).isoformat() if pp else None
        out.append({
            "title": title,
            "url": url,
            "publisher": publisher,
            "published_at": published_at,
            "market": market,
            "isin": isin,
            "holding_name": holding_name,
        })
    return out


def save_items(data_dir: Path, items: list[dict]) -> int:
    if not items:
        return 0
    now = storage.now_iso()
    inserted = 0
    with storage.connect(data_dir) as con:
        for item in items:
            url = item.get("url") or ""
            if not url or not _safe_url(url):
                continue
            cur = con.execute(
                """
                INSERT OR IGNORE INTO news_items(url_hash, title, url, publisher, published_at,
                                                  market, isin, holding_name, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (_url_hash(url), item.get("title") or "", url, item.get("publisher"),
                 item.get("published_at"), item.get("market"), item.get("isin"),
                 item.get("holding_name"), now),
            )
            if cur.rowcount and cur.rowcount > 0:
                inserted += 1
        con.commit()
    return inserted


def _fetch_market_feed(data_dir: Path, market: str) -> int:
    try:
        socket.setdefaulttimeout(FEED_TIMEOUT_SECS)
        parsed = feedparser.parse(market_feed_url(market))
        items = normalize_entries(parsed, market=market, isin=None, holding_name=None)
        return save_items(data_dir, items)
    except Exception:
        return 0


def _fetch_holding_feed(data_dir: Path, market: str, isin: str | None, name: str) -> int:
    try:
        socket.setdefaulttimeout(FEED_TIMEOUT_SECS)
        parsed = feedparser.parse(holding_feed_url(name))
        items = normalize_entries(parsed, market=market, isin=isin, holding_name=name)
        return save_items(data_dir, items)
    except Exception:
        return 0


def _fetch_yfinance_news(data_dir: Path, market: str, isin: str | None, name: str,
                          symbol: str | None) -> int:
    if not symbol:
        return 0
    try:
        socket.setdefaulttimeout(FEED_TIMEOUT_SECS)
        import yfinance as yf
        raw = yf.Ticker(f"{symbol}.NS").news or []
        items = []
        for entry in raw[:HOLDING_FEED_CAP]:
            title = entry.get("title") or entry.get("content", {}).get("title")
            url = (entry.get("link")
                   or entry.get("content", {}).get("canonicalUrl", {}).get("url"))
            publisher = (entry.get("publisher")
                         or entry.get("content", {}).get("provider", {}).get("displayName"))
            if not title or not url:
                continue
            items.append({
                "title": title, "url": url, "publisher": publisher,
                "published_at": None, "market": market, "isin": isin, "holding_name": name,
            })
        return save_items(data_dir, items)
    except Exception:
        return 0


def fetch_all(data_dir: Path, pf) -> dict:
    market_count = 0
    for market in MARKETS:
        market_count += _fetch_market_feed(data_dir, market)

    holding_count = 0
    if pf is not None:
        holdings = sorted(pf.consolidated(), key=lambda c: -c.value)[:TOP_HOLDINGS_CAP]
        for holding in holdings:
            name = getattr(holding, "name", None)
            isin = getattr(holding, "isin", None)
            symbol = getattr(holding, "nse_symbol", None)
            if not name:
                continue
            holding_count += _fetch_holding_feed(data_dir, "India", isin, name)
            holding_count += _fetch_yfinance_news(data_dir, "India", isin, name, symbol)

    try:
        prune(data_dir)
    except Exception:
        pass
    return {"holdings": holding_count, "markets": market_count}


def load_items(data_dir: Path, market: str | None = None, mine: bool = False,
               within_hours: int | None = None, limit: int = 50) -> list[dict]:
    conditions = []
    params: list = []
    if market:
        conditions.append("market = ?")
        params.append(market)
    if mine:
        conditions.append("isin IS NOT NULL")
    if within_hours is not None:
        cutoff = (datetime.now() - timedelta(hours=within_hours)).replace(microsecond=0).isoformat()
        conditions.append("fetched_at >= ?")
        params.append(cutoff)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)
    with storage.connect(data_dir) as con:
        rows = con.execute(
            f"""
            SELECT * FROM news_items
            {where}
            ORDER BY COALESCE(published_at, fetched_at) DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def prune(data_dir: Path) -> int:
    cutoff = (datetime.now() - timedelta(days=PRUNE_AFTER_DAYS)).replace(microsecond=0).isoformat()
    with storage.connect(data_dir) as con:
        cur = con.execute(
            f"""
            DELETE FROM news_items
             WHERE fetched_at < ?
                OR id NOT IN (SELECT id FROM news_items ORDER BY fetched_at DESC LIMIT {PRUNE_KEEP})
            """,
            (cutoff,),
        )
        con.commit()
        return cur.rowcount


def last_fetched(data_dir: Path) -> str | None:
    with storage.connect(data_dir) as con:
        row = con.execute("SELECT MAX(fetched_at) AS m FROM news_items").fetchone()
    return row["m"] if row and row["m"] else None
