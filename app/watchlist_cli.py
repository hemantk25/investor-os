"""CLI for watchlist imports — the command Claude Code runs after reading a
TradingView watchlist screenshot the owner pastes.

Usage:
    python -m app.watchlist_cli import "NSE:RELIANCE,NASDAQ:MSFT" \
        --market India --category Stocks --group Custom
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from app import watchlist

BASE = Path(__file__).resolve().parent.parent


def _data_dir() -> Path:
    return Path(os.environ.get("INVESTOR_OS_DATA", str(BASE / "data")))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="watchlist_cli",
                                 description="Import symbols into the Investor OS watchlist.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    imp = sub.add_parser("import", help="Import comma-separated EXCHANGE:SYMBOL entries")
    imp.add_argument("symbols", help='e.g. "NSE:RELIANCE,NASDAQ:MSFT"')
    imp.add_argument("--market", default="Global")
    imp.add_argument("--category", default="Stocks")
    imp.add_argument("--group", default="Custom")
    imp.add_argument("--member", default="All")
    args = ap.parse_args(argv)

    if args.cmd == "import":
        data_dir = _data_dir()
        incoming = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        if not incoming:
            print("No symbols given. Pass a comma-separated list like "
                  '"NSE:RELIANCE,NASDAQ:MSFT".')
            return 2
        existing = {i["symbol"] for i in watchlist.load(data_dir)}
        new = [s for s in incoming if s not in existing]
        skipped = len(incoming) - len(new)
        added = 0
        if new:
            added = watchlist.import_text(data_dir, ",".join(new), market=args.market,
                                          group=args.group, member=args.member,
                                          category=args.category)
        print(f"Imported {added} symbols ({skipped} skipped as already present).")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
