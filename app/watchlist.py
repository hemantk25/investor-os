from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote_plus

from app import storage


MARKETS = ["India", "US", "UAE", "Canada", "Global"]
CATEGORIES = ["Indices", "Stocks", "Technology", "Banks", "Custom"]
SUBCATEGORIES = ["Core", "Large Cap", "Midcap", "Tech", "Dubai", "Abu Dhabi", "Custom"]
GROUPS = ["NSE Key Indices", "Gift Nifty", "NSE Midcap", "UAE Market", "Abu Dhabi",
          "Dubai", "Custom"]
MAX_OPEN_BOARDS = 4

_DEFAULT_ITEMS = [
    ("NSE:NIFTY", "Nifty 50", "India", "Indices", "NSE Key Indices"),
    ("BSE:SENSEX", "Sensex", "India", "Indices", "NSE Key Indices"),
    ("NSE:BANKNIFTY", "Bank Nifty", "India", "Banks", "NSE Key Indices"),
    ("NSEIX:NIFTY1!", "Gift Nifty", "Global", "Indices", "Gift Nifty"),
    ("NSE:CNXMIDCAP", "Nifty Midcap", "India", "Indices", "NSE Midcap"),
    ("NSE:CNXSMALLCAP", "Nifty Smallcap", "India", "Indices", "NSE Midcap"),
    ("DFM:DFMGI", "DFM General Index", "UAE", "Indices", "Dubai"),
    ("ADX:FADGI", "ADX General Index", "UAE", "Indices", "Abu Dhabi"),
    ("NASDAQ:IXIC", "Nasdaq Composite", "US", "Indices", "Technology"),
    ("SP:SPX", "S&P 500", "US", "Indices", "Core"),
    ("TSX:TSX", "TSX Composite", "Canada", "Indices", "Core"),
]


def storage_path(base_dir: Path) -> Path:
    return Path(base_dir) / "watchlists.json"


def _normalise(raw: dict) -> dict:
    symbol = str(raw.get("symbol", "")).strip().upper()
    category = str(raw.get("category") or raw.get("group") or "Custom").strip()
    subcategory = str(raw.get("subcategory") or raw.get("group") or "Custom").strip()
    market = str(raw.get("market", "")).strip() or "Global"
    member = str(raw.get("member", "")).strip() or "All"
    item = {
        "id": raw.get("id"),
        "symbol": symbol,
        "name": str(raw.get("name", "")).strip() or symbol,
        "market": market if market in MARKETS else "Global",
        "category": category if category in CATEGORIES or category in GROUPS else "Custom",
        "subcategory": subcategory if subcategory in SUBCATEGORIES or subcategory in GROUPS else "Custom",
        "member": member,
    }
    item["group"] = item["subcategory"]
    item["url"] = "https://www.tradingview.com/chart/?symbol=" + quote_plus(item["symbol"])
    return item


def _default_dicts() -> list[dict]:
    return [_normalise({"symbol": s, "name": n, "market": m, "category": c,
                        "subcategory": sub, "member": "All"})
            for s, n, m, c, sub in _DEFAULT_ITEMS]


def _insert_item(con, item: dict) -> int:
    now = storage.now_iso()
    cur = con.execute(
        """
        INSERT INTO watchlist_items(symbol, name, market, category, subcategory, member,
                                    created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (item["symbol"], item["name"], item["market"], item["category"],
         item["subcategory"], item["member"], now, now),
    )
    return int(cur.lastrowid)


def _legacy_items(base_dir: Path) -> list[dict]:
    path = storage_path(base_dir)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    return [_normalise(r) for r in raw if isinstance(r, dict) and str(r.get("symbol", "")).strip()]


def ensure_seeded(base_dir: Path) -> None:
    with storage.connect(base_dir) as con:
        item_count = con.execute("SELECT COUNT(*) AS n FROM watchlist_items").fetchone()["n"]
        if item_count == 0:
            for item in (_legacy_items(base_dir) or _default_dicts()):
                _insert_item(con, item)
        board_count = con.execute("SELECT COUNT(*) AS n FROM watchlist_boards").fetchone()["n"]
        if board_count == 0:
            now = storage.now_iso()
            boards = [
                ("India Indices", "India", "Indices", "NSE Key Indices", "All", 0),
                ("UAE Indices", "UAE", "Indices", "Custom", "All", 1),
            ]
            con.executemany(
                """
                INSERT INTO watchlist_boards(title, market, category, subcategory, member,
                                             is_open, sort_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                [(title, market, cat, sub, member, order, now, now)
                 for title, market, cat, sub, member, order in boards],
            )
        con.commit()


def _row_to_item(row) -> dict:
    item = _normalise(dict(row))
    item["id"] = row["id"]
    return item


def load(base_dir: Path) -> list[dict]:
    ensure_seeded(base_dir)
    with storage.connect(base_dir) as con:
        rows = con.execute("SELECT * FROM watchlist_items ORDER BY market, category, name").fetchall()
        return [_row_to_item(r) for r in rows]


def save(base_dir: Path, items: list[dict]) -> None:
    with storage.connect(base_dir) as con:
        con.execute("DELETE FROM watchlist_items")
        for item in items:
            _insert_item(con, _normalise(item))
        con.commit()


def filtered(items: list[dict], q: str = "", market: str = "", member: str | None = None,
             group: str = "", category: str = "", subcategory: str = "",
             limit: int | None = None) -> list[dict]:
    ql = (q or "").strip().lower()
    out = []
    sub = subcategory or group
    for item in items:
        if market and item["market"] != market:
            continue
        if category and item["category"] != category:
            continue
        if sub and item["subcategory"] != sub and item["group"] != sub:
            continue
        if member and item["member"] not in ("All", member):
            continue
        haystack = f"{item['symbol']} {item['name']} {item['market']} {item['category']} {item['subcategory']} {item['member']}".lower()
        if ql and ql not in haystack:
            continue
        out.append(item)
        if limit and len(out) >= limit:
            break
    return out


def add_item(base_dir: Path, data: dict) -> dict | None:
    item = _normalise(data)
    if not item["symbol"]:
        return None
    ensure_seeded(base_dir)
    with storage.connect(base_dir) as con:
        existing = con.execute(
            """
            SELECT id FROM watchlist_items
             WHERE symbol = ? AND market = ? AND category = ? AND subcategory = ? AND member = ?
             LIMIT 1
            """,
            (item["symbol"], item["market"], item["category"], item["subcategory"], item["member"]),
        ).fetchone()
        now = storage.now_iso()
        if existing:
            con.execute(
                "UPDATE watchlist_items SET name = ?, updated_at = ? WHERE id = ?",
                (item["name"], now, existing["id"]),
            )
            item["id"] = existing["id"]
        else:
            item["id"] = _insert_item(con, item)
        con.commit()
    return item


def delete_item(base_dir: Path, item_id: str) -> None:
    ensure_seeded(base_dir)
    with storage.connect(base_dir) as con:
        con.execute("DELETE FROM watchlist_items WHERE id = ?", (item_id,))
        con.commit()


def parse_tradingview_text(text: str, market: str = "Global", group: str = "Custom",
                           member: str = "All", category: str = "Custom",
                           subcategory: str | None = None) -> list[dict]:
    symbols = []
    for token in text.replace("\n", ",").replace("\r", ",").split(","):
        symbol = token.strip()
        if symbol:
            symbols.append(symbol)
    sub = subcategory or group
    return [_normalise({"symbol": symbol, "name": symbol, "market": market,
                        "category": category, "subcategory": sub, "member": member})
            for symbol in symbols]


def import_text(base_dir: Path, text: str, market: str = "Global", group: str = "Custom",
                member: str = "All", category: str = "Custom",
                subcategory: str | None = None) -> int:
    incoming = parse_tradingview_text(text, market, group, member, category, subcategory)
    for item in incoming:
        add_item(base_dir, item)
    return len(incoming)


def export_text(items: list[dict]) -> str:
    return ",".join(item["symbol"] for item in items)


def open_boards(base_dir: Path) -> list[dict]:
    ensure_seeded(base_dir)
    with storage.connect(base_dir) as con:
        rows = con.execute(
            """
            SELECT * FROM watchlist_boards
             WHERE is_open = 1
             ORDER BY sort_order ASC, id ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def create_board(base_dir: Path, data: dict) -> int | None:
    ensure_seeded(base_dir)
    with storage.connect(base_dir) as con:
        open_count = con.execute(
            "SELECT COUNT(*) AS n FROM watchlist_boards WHERE is_open = 1"
        ).fetchone()["n"]
        if open_count >= MAX_OPEN_BOARDS:
            return None
        now = storage.now_iso()
        market = str(data.get("market") or "India")
        category = str(data.get("category") or "Indices")
        subcategory = str(data.get("subcategory") or data.get("group") or "Custom")
        member = str(data.get("member") or "All")
        title = str(data.get("title") or f"{market} · {subcategory}")
        sort_order = con.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 AS n FROM watchlist_boards"
        ).fetchone()["n"]
        cur = con.execute(
            """
            INSERT INTO watchlist_boards(title, market, category, subcategory, member,
                                         is_open, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (title, market, category, subcategory, member, sort_order, now, now),
        )
        con.commit()
        return int(cur.lastrowid)


def close_board(base_dir: Path, board_id: str) -> None:
    with storage.connect(base_dir) as con:
        con.execute("UPDATE watchlist_boards SET is_open = 0, updated_at = ? WHERE id = ?",
                    (storage.now_iso(), board_id))
        con.commit()


def board_items(base_dir: Path, board: dict, q: str = "") -> list[dict]:
    return filtered(load(base_dir), q=q, market=board["market"], member=None if board["member"] == "All" else board["member"],
                    category=board["category"], subcategory=board["subcategory"])


def yahoo_symbol(symbol: str) -> str:
    symbol = (symbol or "").upper()
    special = {
        "NSE:NIFTY": "^NSEI",
        "BSE:SENSEX": "^BSESN",
        "NSE:BANKNIFTY": "^NSEBANK",
        "NSE:CNXMIDCAP": "^NSEMDCP50",
        "NSE:CNXSMALLCAP": "^CNXSC",
        "NASDAQ:IXIC": "^IXIC",
        "SP:SPX": "^GSPC",
        "TSX:TSX": "^GSPTSE",
    }
    if symbol in special:
        return special[symbol]
    if ":" not in symbol:
        return symbol
    exchange, ticker = symbol.split(":", 1)
    if exchange == "NSE":
        return f"{ticker}.NS"
    if exchange == "BSE":
        return f"{ticker}.BO"
    if exchange in ("NASDAQ", "NYSE", "AMEX"):
        return ticker
    if exchange in ("DFM", "ADX"):
        return f"{ticker}.AE"
    if exchange == "TSX":
        return f"{ticker}.TO"
    return ticker


def quote_symbols(items: list[dict]) -> dict[str, str]:
    return {item["symbol"]: yahoo_symbol(item["symbol"]) for item in items}


def save_quote(base_dir: Path, symbol: str, quote, source: str = "yfinance") -> None:
    with storage.connect(base_dir) as con:
        con.execute(
            """
            INSERT INTO quote_snapshots(symbol, price, day_pct, source, fetched_at, payload)
            VALUES (?, ?, ?, ?, ?, '{}')
            ON CONFLICT(symbol) DO UPDATE SET price = excluded.price,
                                             day_pct = excluded.day_pct,
                                             source = excluded.source,
                                             fetched_at = excluded.fetched_at,
                                             payload = excluded.payload
            """,
            (symbol, quote.price, quote.day_pct, source, storage.now_iso()),
        )
        con.commit()


def quote_map(base_dir: Path) -> dict[str, dict]:
    with storage.connect(base_dir) as con:
        rows = con.execute("SELECT * FROM quote_snapshots").fetchall()
        return {r["symbol"]: dict(r) for r in rows}


def with_quotes(base_dir: Path, items: list[dict]) -> list[dict]:
    quotes = quote_map(base_dir)
    out = []
    for item in items:
        row = dict(item)
        quote = quotes.get(item["symbol"])
        row["price"] = quote["price"] if quote else None
        row["day_pct"] = quote["day_pct"] if quote else None
        row["fetched_at"] = quote["fetched_at"] if quote else ""
        row["price_known"] = quote is not None and quote["price"] is not None
        out.append(row)
    return out

