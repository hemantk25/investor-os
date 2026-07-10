from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

from app import parser
from app import storage


def _f(value, default=None):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _s(value, default=""):
    return str(value or default).strip()


def has_manual_holdings(base_dir: Path) -> bool:
    with storage.connect(base_dir) as con:
        row = con.execute(
            "SELECT 1 FROM holding_events WHERE event_type = 'manual' AND active = 1 LIMIT 1"
        ).fetchone()
        return bool(row)


def add_manual(base_dir: Path, data: dict) -> int | None:
    member = _s(data.get("member"), "PK")
    name = _s(data.get("name"))
    isin = _s(data.get("isin")).upper()
    symbol = _s(data.get("symbol")).upper()
    qty = _f(data.get("qty"), 0.0) or 0.0
    if not name or not isin or qty <= 0:
        return None
    now = storage.now_iso()
    with storage.connect(base_dir) as con:
        cur = con.execute(
            """
            INSERT INTO holding_events(event_type, active, member, name, isin, symbol, qty,
                                       avg_cost, price, day_pct, asset_class, notes,
                                       created_at, updated_at)
            VALUES ('manual', 1, ?, ?, ?, ?, ?, ?, ?, ?, 'equity', ?, ?, ?)
            """,
            (member, name, isin, symbol, qty, _f(data.get("avg_cost")),
             _f(data.get("price")), _f(data.get("day_pct")), _s(data.get("notes")),
             now, now),
        )
        con.commit()
        return int(cur.lastrowid)


def edit_manual(base_dir: Path, event_id: int, data: dict) -> None:
    now = storage.now_iso()
    with storage.connect(base_dir) as con:
        con.execute(
            """
            UPDATE holding_events
               SET member = ?, name = ?, isin = ?, symbol = ?, qty = ?,
                   avg_cost = ?, price = ?, day_pct = ?, notes = ?, updated_at = ?
             WHERE id = ? AND event_type = 'manual'
            """,
            (_s(data.get("member"), "PK"), _s(data.get("name")),
             _s(data.get("isin")).upper(), _s(data.get("symbol")).upper(),
             _f(data.get("qty"), 0.0) or 0.0, _f(data.get("avg_cost")),
             _f(data.get("price")), _f(data.get("day_pct")),
             _s(data.get("notes")), now, event_id),
        )
        con.commit()


def delete_manual(base_dir: Path, event_id: int) -> None:
    now = storage.now_iso()
    with storage.connect(base_dir) as con:
        con.execute(
            "UPDATE holding_events SET active = 0, updated_at = ? WHERE id = ? AND event_type = 'manual'",
            (now, event_id),
        )
        con.commit()


def add_sell(base_dir: Path, data: dict) -> int | None:
    member = _s(data.get("member"), "PK")
    isin = _s(data.get("isin")).upper()
    qty = _f(data.get("qty"), 0.0) or 0.0
    if not member or not isin or qty <= 0:
        return None
    now = storage.now_iso()
    with storage.connect(base_dir) as con:
        cur = con.execute(
            """
            INSERT INTO holding_events(event_type, active, member, name, isin, symbol, qty,
                                       notes, created_at, updated_at)
            VALUES ('sell', 1, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (member, _s(data.get("name")), isin, _s(data.get("symbol")).upper(),
             qty, _s(data.get("notes")), now, now),
        )
        con.commit()
        return int(cur.lastrowid)


def list_manual(base_dir: Path) -> list[dict]:
    with storage.connect(base_dir) as con:
        rows = con.execute(
            """
            SELECT * FROM holding_events
             WHERE event_type = 'manual' AND active = 1
             ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def symbol_map(base_dir: Path) -> dict[str, str]:
    out = {}
    for row in list_manual(base_dir):
        if row.get("isin") and row.get("symbol"):
            out[row["isin"]] = row["symbol"]
    return out


def _manual_holdings(base_dir: Path) -> list:
    holdings = []
    for row in list_manual(base_dir):
        h = parser.Holding(
            member=row["member"],
            name=row["name"],
            icici_symbol=row["symbol"] or "",
            isin=row["isin"],
            qty=float(row["qty"] or 0),
            avg_cost=row["avg_cost"],
            excel_cmp=row["price"],
            excel_day_pct=row["day_pct"],
        )
        h.source = "manual"
        h.source_id = row["id"]
        holdings.append(h)
    return holdings


def _sell_events(base_dir: Path) -> list[dict]:
    with storage.connect(base_dir) as con:
        rows = con.execute(
            """
            SELECT * FROM holding_events
             WHERE event_type = 'sell' AND active = 1
             ORDER BY created_at ASC, id ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def _apply_sell(holdings: list, event: dict) -> list:
    remaining = float(event["qty"] or 0)
    out = []
    for h in holdings:
        if remaining > 0 and h.member == event["member"] and h.isin == event["isin"]:
            take = min(float(h.qty), remaining)
            remaining -= take
            new_qty = float(h.qty) - take
            if new_qty > 0:
                out.append(replace(h, qty=new_qty))
        else:
            out.append(h)
    return out


def apply_events(pr: parser.ParseResult, base_dir: Path) -> parser.ParseResult:
    holdings = list(pr.holdings) + _manual_holdings(base_dir)
    for event in _sell_events(base_dir):
        holdings = _apply_sell(holdings, event)
    members = sorted(set(pr.members) | {h.member for h in holdings})
    return parser.ParseResult(holdings=holdings, skipped=pr.skipped, asof=pr.asof,
                              members=members)


def empty_parse_result(base_dir: Path):
    from datetime import datetime

    pr = parser.ParseResult(holdings=[], skipped=[], asof=datetime.now(), members=[])
    return apply_events(pr, base_dir)


def record_snapshot(base_dir: Path, pf) -> int:
    today = date.today().isoformat()
    rows = []
    for member in ["All"] + pf.members:
        selected = None if member == "All" else member
        t = pf.totals(selected)
        rows.append((today, member, t.total_value, t.invested_known, t.pl, t.day_pl,
                     json.dumps({"pl_pct": t.pl_pct, "day_pl_pct": t.day_pl_pct}),
                     storage.now_iso()))
    with storage.connect(base_dir) as con:
        con.executemany(
            """
            INSERT INTO portfolio_snapshots(snapshot_date, member, total_value, invested_known,
                                            pl, day_pl, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(snapshot_date, member) DO UPDATE SET
              total_value = excluded.total_value,
              invested_known = excluded.invested_known,
              pl = excluded.pl,
              day_pl = excluded.day_pl,
              payload = excluded.payload,
              created_at = excluded.created_at
            """,
            rows,
        )
        con.commit()
    return len(rows)


def snapshot_count(base_dir: Path) -> int:
    with storage.connect(base_dir) as con:
        row = con.execute("SELECT COUNT(*) AS n FROM portfolio_snapshots").fetchone()
        return int(row["n"] if row else 0)

