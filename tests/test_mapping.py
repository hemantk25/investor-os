import app.mapping as mapping


def _write(p, text):
    p.write_text(text, encoding="utf-8")


def _raise(*a, **k):
    raise RuntimeError("offline")


def test_cache_and_overrides_precedence(tmp_path, monkeypatch):
    monkeypatch.setattr(mapping, "_download_nse_list", _raise)
    _write(tmp_path / "isin-map.csv", "isin,symbol\nINE001A01001,ALPHAMOT\nINE004D01034,DELTABANK\n")
    _write(tmp_path / "overrides.csv", "isin,symbol\nINE004D01034,DELTAB\n")
    m = mapping.ensure_map(tmp_path)
    assert m["INE001A01001"] == "ALPHAMOT"
    assert m["INE004D01034"] == "DELTAB"          # override wins


def test_no_cache_offline_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(mapping, "_download_nse_list", _raise)
    assert mapping.ensure_map(tmp_path) == {}


def test_download_writes_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(mapping, "_download_nse_list", lambda: {"INE001A01001": "ALPHAMOT"})
    m = mapping.ensure_map(tmp_path, refresh=True)
    assert m == {"INE001A01001": "ALPHAMOT"}
    assert (tmp_path / "isin-map.csv").exists()
