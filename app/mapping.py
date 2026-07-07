from __future__ import annotations

import csv
import io
from pathlib import Path

import requests

NSE_URLS = ["https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
            "https://archives.nseindia.com/content/equities/EQUITY_L.csv"]
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36"}


def _download_nse_list() -> dict[str, str]:
    last = None
    for url in NSE_URLS:
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            out = {}
            for row in csv.DictReader(io.StringIO(r.text)):
                row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
                if row.get("ISIN NUMBER") and row.get("SYMBOL"):
                    out[row["ISIN NUMBER"]] = row["SYMBOL"]
            if out:
                return out
        except Exception as e:
            last = e
    raise RuntimeError(f"NSE list download failed: {last}")


def _read_csv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return {r["isin"]: r["symbol"] for r in csv.DictReader(f) if r.get("isin")}


def ensure_map(data_dir: Path, refresh: bool = False) -> dict[str, str]:
    data_dir.mkdir(parents=True, exist_ok=True)
    cache = data_dir / "isin-map.csv"
    if refresh or not cache.exists():
        try:
            fresh = _download_nse_list()
            with cache.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["isin", "symbol"])
                for k, v in sorted(fresh.items()):
                    w.writerow([k, v])
        except Exception:
            pass  # fall through to whatever cache exists
    result = _read_csv(cache)
    result.update(_read_csv(data_dir / "overrides.csv"))
    return result
