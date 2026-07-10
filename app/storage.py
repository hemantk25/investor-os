from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


DB_NAME = "investor_os.sqlite"


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def db_path(base_dir: Path) -> Path:
    return Path(base_dir) / DB_NAME


def connect(base_dir: Path) -> sqlite3.Connection:
    path = db_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    init_db(con)
    return con


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS holding_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          event_type TEXT NOT NULL,
          active INTEGER NOT NULL DEFAULT 1,
          member TEXT NOT NULL,
          name TEXT,
          isin TEXT,
          symbol TEXT,
          qty REAL NOT NULL DEFAULT 0,
          avg_cost REAL,
          price REAL,
          day_pct REAL,
          asset_class TEXT NOT NULL DEFAULT 'equity',
          notes TEXT,
          target_event_id INTEGER,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          snapshot_date TEXT NOT NULL,
          member TEXT NOT NULL,
          total_value REAL NOT NULL,
          invested_known REAL NOT NULL,
          pl REAL NOT NULL,
          day_pl REAL NOT NULL,
          payload TEXT NOT NULL,
          created_at TEXT NOT NULL,
          UNIQUE(snapshot_date, member)
        );

        CREATE TABLE IF NOT EXISTS watchlist_boards (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          market TEXT NOT NULL,
          category TEXT NOT NULL,
          subcategory TEXT NOT NULL,
          member TEXT NOT NULL DEFAULT 'All',
          is_open INTEGER NOT NULL DEFAULT 1,
          sort_order INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS watchlist_items (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          symbol TEXT NOT NULL,
          name TEXT NOT NULL,
          market TEXT NOT NULL,
          category TEXT NOT NULL,
          subcategory TEXT NOT NULL,
          member TEXT NOT NULL DEFAULT 'All',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS quote_snapshots (
          symbol TEXT PRIMARY KEY,
          price REAL,
          day_pct REAL,
          source TEXT NOT NULL DEFAULT 'yfinance',
          fetched_at TEXT NOT NULL,
          payload TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS app_state (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS news_items (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          url_hash TEXT NOT NULL UNIQUE,
          title TEXT NOT NULL, url TEXT NOT NULL,
          publisher TEXT, published_at TEXT,
          market TEXT NOT NULL,
          isin TEXT,
          holding_name TEXT,
          fetched_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS security_meta (
          symbol TEXT PRIMARY KEY,
          market_cap REAL, sector TEXT, industry TEXT,
          fetched_at TEXT NOT NULL
        );
        """
    )
    con.commit()


def get_state(base_dir: Path, key: str) -> str | None:
    with connect(base_dir) as con:
        row = con.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def set_state(base_dir: Path, key: str, value: str) -> None:
    now = now_iso()
    with connect(base_dir) as con:
        con.execute(
            """
            INSERT INTO app_state(key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value,
                                           updated_at = excluded.updated_at
            """,
            (key, value, now),
        )
        con.commit()

