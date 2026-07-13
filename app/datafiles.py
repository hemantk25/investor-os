from __future__ import annotations

from pathlib import Path

_EXCLUDE_PREFIX = "~$"
_EXCLUDE_SUFFIX = ".tmp"


def _candidates(data_dir: Path, subdir: str, flat_name: str) -> list[Path]:
    out: list[Path] = []
    sub = Path(data_dir) / subdir
    if sub.is_dir():
        out.extend(p for p in sub.glob("*.xlsx") if p.is_file())
    flat = Path(data_dir) / flat_name
    if flat.is_file():
        out.append(flat)
    out = [p for p in out
           if not p.name.startswith(_EXCLUDE_PREFIX) and not p.name.endswith(_EXCLUDE_SUFFIX)]
    return sorted(out, key=lambda p: p.stat().st_mtime, reverse=True)


def holdings_candidates(data_dir) -> list[Path]:
    return _candidates(Path(data_dir), "holdings", "holdings.xlsx")


def advisory_candidates(data_dir) -> list[Path]:
    return _candidates(Path(data_dir), "advisory", "advisory.xlsx")


def latest_holdings(data_dir) -> Path | None:
    c = holdings_candidates(data_dir)
    return c[0] if c else None


def latest_advisory(data_dir) -> Path | None:
    c = advisory_candidates(data_dir)
    return c[0] if c else None


def resolve_and_parse_holdings(data_dir):
    """Try candidates newest-first; skip unparseable files with a warning.

    Returns (ParseResult | None, Path | None, warnings: list[str]).
    """
    from app import parser

    warnings: list[str] = []
    for path in holdings_candidates(data_dir):
        try:
            return parser.parse_holdings(path), path, warnings
        except Exception as exc:
            warnings.append(
                f"could not read {path.name} ({type(exc).__name__}) — trying next file")
    return None, None, warnings
