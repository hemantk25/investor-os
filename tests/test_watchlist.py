from app import watchlist as wmod


def test_default_watchlist_has_requested_markets(tmp_path):
    items = wmod.load(tmp_path)
    assert any(i["group"] == "NSE Key Indices" for i in items)
    assert any(i["group"] == "Gift Nifty" for i in items)
    assert any(i["market"] == "UAE" for i in items)
    assert any(i["market"] == "Canada" for i in items)


def test_filter_member_keeps_family_items(tmp_path):
    wmod.add_item(tmp_path, {"symbol": "NSE:TCS", "name": "TCS", "market": "India",
                             "group": "Custom", "member": "PK"})
    items = wmod.filtered(wmod.load(tmp_path), member="PK")
    symbols = [i["symbol"] for i in items]
    assert "NSE:TCS" in symbols
    assert "NSE:NIFTY" in symbols


def test_tradingview_text_roundtrip(tmp_path):
    count = wmod.import_text(tmp_path, "NASDAQ:AAPL, NSE:RELIANCE\nDFM:DFMGI",
                             market="Global", group="Custom", member="All")
    assert count == 3
    custom = wmod.filtered(wmod.load(tmp_path), group="Custom")
    exported = wmod.export_text(custom)
    assert "NASDAQ:AAPL" in exported
    assert "NSE:RELIANCE" in exported


def test_open_boards_are_limited_and_closable(tmp_path):
    boards = wmod.open_boards(tmp_path)
    assert boards
    for idx in range(wmod.MAX_OPEN_BOARDS - len(boards)):
        assert wmod.create_board(tmp_path, {"title": f"Board {idx}", "market": "US",
                                           "category": "Stocks",
                                           "subcategory": "Tech"})
    assert wmod.create_board(tmp_path, {"title": "Too many", "market": "Canada",
                                       "category": "Stocks",
                                       "subcategory": "Custom"}) is None
    first = wmod.open_boards(tmp_path)[0]
    wmod.close_board(tmp_path, str(first["id"]))
    assert all(b["id"] != first["id"] for b in wmod.open_boards(tmp_path))


def test_quote_snapshots_enrich_items(tmp_path):
    from app.prices import Quote

    item = wmod.add_item(tmp_path, {"symbol": "NASDAQ:MSFT", "name": "Microsoft",
                                    "market": "US", "category": "Technology",
                                    "subcategory": "Tech"})
    wmod.save_quote(tmp_path, item["symbol"], Quote(410.0, 1.2))
    enriched = wmod.with_quotes(tmp_path, [item])[0]
    assert enriched["price_known"]
    assert enriched["price"] == 410.0
