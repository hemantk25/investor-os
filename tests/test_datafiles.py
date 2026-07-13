from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from app import datafiles

FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"


def _touch(p: Path, mtime_offset: float = 0):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")
    t = time.time() + mtime_offset
    os.utime(p, (t, t))


def test_newest_wins_across_subfolder_and_flat(tmp_path):
    _touch(tmp_path / "holdings.xlsx", -100)          # flat, oldest
    _touch(tmp_path / "holdings" / "july.xlsx", -50)
    _touch(tmp_path / "holdings" / "latest.xlsx", 0)  # newest
    assert datafiles.latest_holdings(tmp_path).name == "latest.xlsx"
    names = [p.name for p in datafiles.holdings_candidates(tmp_path)]
    assert names == ["latest.xlsx", "july.xlsx", "holdings.xlsx"]


def test_tmp_and_lock_files_ignored(tmp_path):
    _touch(tmp_path / "holdings" / "~$open.xlsx", 10)
    _touch(tmp_path / "holdings" / "real.xlsx", 0)
    _touch(tmp_path / "holdings" / "part.tmp", 20)
    assert datafiles.latest_holdings(tmp_path).name == "real.xlsx"


def test_empty_returns_none(tmp_path):
    assert datafiles.latest_holdings(tmp_path) is None
    assert datafiles.latest_advisory(tmp_path) is None


def test_advisory_resolution(tmp_path):
    _touch(tmp_path / "advisory.xlsx", -10)
    _touch(tmp_path / "advisory" / "new-report.xlsx", 0)
    assert datafiles.latest_advisory(tmp_path).name == "new-report.xlsx"


def test_resolve_and_parse_falls_back_on_corrupt(tmp_path):
    (tmp_path / "holdings").mkdir(parents=True, exist_ok=True)
    shutil.copy(FIX, tmp_path / "holdings" / "good.xlsx")
    old = time.time() - 100
    os.utime(tmp_path / "holdings" / "good.xlsx", (old, old))
    _touch(tmp_path / "holdings" / "corrupt.xlsx", 100)   # newest but not a real xlsx
    pr, path, warns = datafiles.resolve_and_parse_holdings(tmp_path)
    assert path.name == "good.xlsx"
    assert pr is not None and len(pr.holdings) > 0
    assert any("corrupt.xlsx" in w for w in warns)


def test_resolve_none_when_nothing(tmp_path):
    pr, path, warns = datafiles.resolve_and_parse_holdings(tmp_path)
    assert pr is None and path is None and warns == []
