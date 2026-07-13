from app import watchlist, watchlist_cli


def test_import_adds_and_dedupes(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("INVESTOR_OS_DATA", str(tmp_path))
    rc = watchlist_cli.main(["import", "NSE:RELIANCE,NASDAQ:MSFT",
                             "--market", "India", "--category", "Stocks",
                             "--group", "Custom"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "2" in out
    symbols = {i["symbol"] for i in watchlist.load(tmp_path)}
    assert {"NSE:RELIANCE", "NASDAQ:MSFT"} <= symbols

    before = len(watchlist.load(tmp_path))
    rc2 = watchlist_cli.main(["import", "NSE:RELIANCE", "--market", "India"])
    assert rc2 == 0
    assert len(watchlist.load(tmp_path)) == before          # no duplicate row
    assert "skipped" in capsys.readouterr().out.lower()


def test_import_empty_is_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("INVESTOR_OS_DATA", str(tmp_path))
    assert watchlist_cli.main(["import", "   "]) == 2
    assert "No symbols" in capsys.readouterr().out
