from __future__ import annotations

import hashlib
import json
import re
import socket
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import feedparser

from app import storage


MARKETS = ["Global", "India", "US", "UAE", "Canada"]

MARKET_FEED_CAP = 25
HOLDING_FEED_CAP = 10
TOP_HOLDINGS_CAP = 40
PRUNE_KEEP = 500
PRUNE_AFTER_DAYS = 14
FEED_TIMEOUT_SECS = 10

LOCALES = {"India": ("en-IN", "IN", "IN:en"), "US": ("en-US", "US", "US:en"),
           "UAE": ("en-AE", "AE", "AE:en"), "Canada": ("en-CA", "CA", "CA:en"),
           "Global": ("en-US", "US", "US:en")}
QUERIES = {"India": "Nifty OR Sensex OR Indian stock market OR Indian business",
           "US": "US stock market OR S&P 500 OR Nasdaq OR Wall Street",
           "UAE": "UAE stocks OR DFM OR ADX OR Gulf business",
           "Canada": "TSX OR Canadian stock market OR Canada business",
           "Global": "global markets OR world economy OR oil OR rates"}

SOURCES = {
    "Global": [
        ("Bloomberg", "bloomberg.com"),
        ("Wall Street Journal", "wsj.com"),
        ("Economist", "economist.com"),
        ("Financial Times", "ft.com"),
        ("Reuters", "reuters.com"),
        ("Yahoo Finance", "finance.yahoo.com"),
        ("CNBC", "cnbc.com"),
        ("Forbes", "forbes.com"),
        ("Fortune", "fortune.com"),
    ],
    "US": [
        ("Bloomberg", "bloomberg.com"),
        ("Wall Street Journal", "wsj.com"),
        ("Economist", "economist.com"),
        ("Financial Times", "ft.com"),
        ("Reuters", "reuters.com"),
        ("Morningstar", "morningstar.com"),
        ("Yahoo Finance", "finance.yahoo.com"),
        ("CNBC", "cnbc.com"),
        ("Forbes", "forbes.com"),
        ("Fortune", "fortune.com"),
    ],
    "India": [
        ("Economic Times", "economictimes.indiatimes.com"),
        ("Mint", "livemint.com"),
        ("Business Standard", "business-standard.com"),
        ("Financial Express", "financialexpress.com"),
        ("Business Line", "thehindubusinessline.com"),
        ("Moneycontrol", "moneycontrol.com"),
        ("Yahoo Finance", "finance.yahoo.com"),
    ],
    "Canada": [
        ("BNN Bloomberg", "bnnbloomberg.ca"),
        ("The Globe and Mail", "theglobeandmail.com"),
        ("Yahoo Finance Canada", "ca.finance.yahoo.com"),
        ("Financial Post", "financialpost.com"),
    ],
    "UAE": [
        ("Reuters", "reuters.com"),
        ("Yahoo Finance", "finance.yahoo.com"),
        ("Gulf News", "gulfnews.com"),
        ("Arabian Business", "arabianbusiness.com"),
        ("Khaleej Times", "khaleejtimes.com"),
        ("Forbes Middle East", "forbesmiddleeast.com"),
        ("CNBC Arabia", "cnbcarabia.com"),
        ("The National", "thenationalnews.com"),
    ],
}

_TITLE_SOURCE_SUFFIX_RE = re.compile(r"\s+[-–|]\s+[^-–|]{2,80}$")
_QUARTER_RE = re.compile(r"\b(?:q([1-4])|quarter\s*([1-4]))\b", re.IGNORECASE)
_EARNINGS_RE = re.compile(
    r"\b(q[1-4]|quarter\s*[1-4]|quarterly|results?|earnings?|profit|revenue)\b",
    re.IGNORECASE,
)
_SPLIT_EARNINGS_RE = re.compile(
    r"\b(q[1-4]|quarter\s*[1-4]|quarterly|results?|earnings?|profit|revenue|share price)\b",
    re.IGNORECASE,
)


def _source_clause(market: str) -> str:
    terms = []
    for name, domain in SOURCES.get(market, []):
        if domain:
            terms.append(f"site:{domain}")
        else:
            terms.append(f'"{name}"')
    return " OR ".join(terms)


def market_query(market: str) -> str:
    base = QUERIES[market]
    sources = _source_clause(market)
    return f"({base}) ({sources})" if sources else base


def market_feed_url(market: str) -> str:
    hl, gl, ceid = LOCALES[market]
    return ("https://news.google.com/rss/search?q=" + quote_plus(market_query(market))
            + f"&hl={hl}&gl={gl}&ceid={quote_plus(ceid)}")


def holding_feed_url(name: str) -> str:
    return ("https://news.google.com/rss/search?q=" + quote_plus(f'"{name}" NSE')
            + "&hl=en-IN&gl=IN&ceid=" + quote_plus("IN:en"))


def _url_hash(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()


def _safe_url(url: str) -> bool:
    try:
        return urlparse(url).scheme in ("http", "https")
    except ValueError:
        return False


def _ordered(tags) -> list[str]:
    return [m for m in MARKETS if m in set(tags)]


def _infer_markets(title: str, primary: str) -> list[str]:
    text = (title or "").lower()
    tags = {primary}
    if any(k in text for k in ["global", "world", "oil", "crude", "war", "rates", "dollar"]):
        tags.add("Global")
    if any(k in text for k in ["india", "nifty", "sensex", "rupee", "rbi", "mumbai"]):
        tags.add("India")
    if any(k in text for k in ["us ", "u.s.", "wall street", "s&p", "nasdaq", "fed"]):
        tags.add("US")
    if any(k in text for k in ["uae", "dubai", "abu dhabi", "dfm", "adx", "gulf"]):
        tags.add("UAE")
    if any(k in text for k in ["canada", "tsx", "toronto", "loonie"]):
        tags.add("Canada")
    return _ordered(tags)


def _encode_markets(markets: list[str]) -> str:
    return json.dumps(_ordered(markets))


def _decode_markets(value: str | None, fallback: str | None = None) -> list[str]:
    if value:
        try:
            raw = json.loads(value)
            if isinstance(raw, list):
                return _ordered([str(x) for x in raw])
        except Exception:
            pass
    return _ordered([fallback] if fallback else [])


def _clean_title(title: str) -> str:
    text = _TITLE_SOURCE_SUFFIX_RE.sub("", (title or "").lower())
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _earnings_company_key(title: str) -> str:
    if not _EARNINGS_RE.search(title or ""):
        return ""
    head = _SPLIT_EARNINGS_RE.split(title or "", maxsplit=1)[0]
    head = re.sub(r"\b(today|live|updates?|stock|shares?|price|market)\b", " ", head,
                  flags=re.IGNORECASE)
    words = _clean_title(head).split()
    return " ".join(words[:6])


def _quarter_score(title: str) -> int:
    scores = {"1": 4, "4": 3, "3": 2, "2": 1}
    found = [scores.get(a or b, 0) for a, b in _QUARTER_RE.findall(title or "")]
    if found:
        return max(found)
    if _EARNINGS_RE.search(title or ""):
        return 5
    return 0


def _news_score(item: dict, original_index: int) -> tuple:
    return (
        1 if item.get("holding_name") else 0,
        _quarter_score(item.get("title") or ""),
        item.get("published_at") or item.get("fetched_at") or "",
        -original_index,
    )


def quality_filter_items(items: list[dict], limit: int = 50) -> list[dict]:
    seen_titles: set[str] = set()
    normal_items: list[tuple[int, dict]] = []
    earnings_groups: dict[str, tuple[int, dict]] = {}

    for idx, item in enumerate(items):
        title_key = _clean_title(item.get("title") or "")
        if item.get("holding_name"):
            title_key = f"{title_key}|holding:{item.get('isin') or item.get('holding_name')}"
        if title_key and title_key in seen_titles:
            continue
        if title_key:
            seen_titles.add(title_key)

        company_key = _earnings_company_key(item.get("title") or "")
        if company_key:
            current = earnings_groups.get(company_key)
            if current is None or _news_score(item, idx) > _news_score(current[1], current[0]):
                earnings_groups[company_key] = (idx, item)
            continue
        normal_items.append((idx, item))

    combined = normal_items + list(earnings_groups.values())
    combined.sort(key=lambda row: row[0])
    return [item for _, item in combined[:limit]]


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
            "markets": _infer_markets(title, market),
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
            market = item.get("market") or "Global"
            markets = item.get("markets") or [market]
            cur = con.execute(
                """
                INSERT OR IGNORE INTO news_items(url_hash, title, url, publisher, published_at,
                                                  market, markets, isin, holding_name, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (_url_hash(url), item.get("title") or "", url, item.get("publisher"),
                 item.get("published_at"), market, _encode_markets(markets),
                 item.get("isin"), item.get("holding_name"), now),
            )
            if cur.rowcount and cur.rowcount > 0:
                inserted += 1
                continue
            row = con.execute(
                "SELECT market, markets FROM news_items WHERE url_hash = ?",
                (_url_hash(url),),
            ).fetchone()
            existing = _decode_markets(row["markets"] if row else None,
                                       row["market"] if row else None)
            merged = _ordered(existing + list(markets) + [market])
            con.execute(
                """
                UPDATE news_items
                   SET markets = ?, fetched_at = ?,
                       publisher = COALESCE(publisher, ?),
                       published_at = COALESCE(published_at, ?)
                 WHERE url_hash = ?
                """,
                (_encode_markets(merged), now, item.get("publisher"),
                 item.get("published_at"), _url_hash(url)),
            )
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
                "published_at": None, "market": market,
                "markets": _infer_markets(title, market),
                "isin": isin, "holding_name": name,
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
        conditions.append("(market = ? OR markets LIKE ?)")
        params.extend([market, f'%"{market}"%'])
    if mine:
        conditions.append("isin IS NOT NULL")
    if within_hours is not None:
        cutoff = (datetime.now() - timedelta(hours=within_hours)).replace(microsecond=0).isoformat()
        conditions.append("fetched_at >= ?")
        params.append(cutoff)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    fetch_limit = limit if limit > 500 else max(limit * 3, 100)
    params.append(fetch_limit)
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
    out = []
    for row in rows:
        item = dict(row)
        item["markets_list"] = _decode_markets(item.get("markets"), item.get("market"))
        out.append(item)
    return quality_filter_items(out, limit)


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
