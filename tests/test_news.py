from __future__ import annotations

from datetime import datetime, timedelta

import feedparser

from app import news, storage


RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Reliance wins big order</title><link>https://example.com/a1</link>
<source url="https://ex.com">Mint</source><pubDate>Tue, 07 Jul 2026 04:00:00 GMT</pubDate></item>
<item><title>Dup story</title><link>https://example.com/a1</link></item>
<item><title>Nifty ends higher</title><link>https://example.com/a2</link></item>
</channel></rss>"""


def test_normalize_entries():
    parsed = feedparser.parse(RSS)
    items = news.normalize_entries(parsed, market="India", isin="INE002A01018",
                                    holding_name="Reliance Industries")
    assert len(items) == 3
    first = items[0]
    assert first["title"] == "Reliance wins big order"
    assert first["url"] == "https://example.com/a1"
    assert first["publisher"] == "Mint"
    assert first["published_at"] == datetime(2026, 7, 7, 4, 0, 0).isoformat()
    assert first["market"] == "India"
    assert first["isin"] == "INE002A01018"
    assert first["holding_name"] == "Reliance Industries"
    # second/third entries have no <source> or <pubDate>
    assert items[1]["publisher"] is None
    assert items[1]["published_at"] is None


def test_save_dedupes_by_url(tmp_path):
    parsed = feedparser.parse(RSS)
    items = news.normalize_entries(parsed, market="India", isin=None, holding_name=None)
    inserted = news.save_items(tmp_path, items)
    assert inserted == 2  # 3 items, but two share the same url -> 2 unique rows

    inserted_again = news.save_items(tmp_path, items)
    assert inserted_again == 0


def test_load_filters(tmp_path):
    parsed = feedparser.parse(RSS)
    market_items = news.normalize_entries(parsed, market="India", isin=None, holding_name=None)
    news.save_items(tmp_path, market_items)

    holding_items = news.normalize_entries(parsed, market="India", isin="INE002A01018",
                                            holding_name="Reliance Industries")
    for item in holding_items:
        item["url"] = item["url"].replace("example.com", "holding.example.com")
    news.save_items(tmp_path, holding_items)

    india_items = news.load_items(tmp_path, market="India")
    assert len(india_items) >= 3

    mine_items = news.load_items(tmp_path, mine=True)
    assert mine_items
    assert all(i["isin"] for i in mine_items)

    # within_hours filters on fetched_at, not published_at: the fixture's pubDate is
    # in the past, but everything was just saved so it must still be "within 1 hour".
    recent_items = news.load_items(tmp_path, within_hours=1)
    assert any(i["url"] == "https://example.com/a1" for i in recent_items)

    # age one row's fetched_at manually and confirm it drops out of the within_hours window
    old_time = (datetime.now() - timedelta(hours=5)).replace(microsecond=0).isoformat()
    with storage.connect(tmp_path) as con:
        con.execute("UPDATE news_items SET fetched_at = ? WHERE url = ?",
                    (old_time, "https://example.com/a2"))
        con.commit()
    recent_items_2 = news.load_items(tmp_path, within_hours=1)
    assert all(i["url"] != "https://example.com/a2" for i in recent_items_2)


def test_load_items_orders_newest_first(tmp_path):
    with storage.connect(tmp_path) as con:
        now = storage.now_iso()
        con.executemany(
            """
            INSERT INTO news_items(url_hash, title, url, publisher, published_at, market,
                                    isin, holding_name, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("h1", "Older", "https://example.com/older", "Mint",
                 "2026-01-01T00:00:00", "India", None, None, now),
                ("h2", "Newer", "https://example.com/newer", "Mint",
                 "2026-07-01T00:00:00", "India", None, None, now),
            ],
        )
        con.commit()
    items = news.load_items(tmp_path, market="India")
    titles = [i["title"] for i in items]
    assert titles.index("Newer") < titles.index("Older")


def test_prune_keeps_recent(tmp_path):
    old_time = (datetime.now() - timedelta(days=20)).replace(microsecond=0).isoformat()
    fresh_time = storage.now_iso()
    with storage.connect(tmp_path) as con:
        con.executemany(
            """
            INSERT INTO news_items(url_hash, title, url, publisher, published_at, market,
                                    isin, holding_name, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [(f"old{i}", f"Old {i}", f"https://example.com/old{i}", None, None,
              "India", None, None, old_time) for i in range(3)],
        )
        con.execute(
            """
            INSERT INTO news_items(url_hash, title, url, publisher, published_at, market,
                                    isin, holding_name, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("fresh", "Fresh", "https://example.com/fresh", None, None,
             "India", None, None, fresh_time),
        )
        con.commit()

    deleted = news.prune(tmp_path)
    assert deleted == 3

    with storage.connect(tmp_path) as con:
        rows = con.execute("SELECT title FROM news_items").fetchall()
    remaining = {r["title"] for r in rows}
    assert remaining == {"Fresh"}


def test_feed_urls():
    us_url = news.market_feed_url("US")
    assert "gl=US" in us_url

    holding_url = news.holding_feed_url("Tata Power")
    assert "%22Tata+Power%22" in holding_url
    assert "ceid=IN" in holding_url


def test_last_fetched_none_when_empty(tmp_path):
    assert news.last_fetched(tmp_path) is None


def test_last_fetched_returns_latest(tmp_path):
    parsed = feedparser.parse(RSS)
    items = news.normalize_entries(parsed, market="India", isin=None, holding_name=None)
    news.save_items(tmp_path, items)
    assert news.last_fetched(tmp_path) is not None


def test_normalize_caps_items():
    """Test that normalize_entries respects market (25) and holding (10) caps."""
    items_xml = ""
    for i in range(30):
        items_xml += f'<item><title>Item {i}</title><link>https://example.com/x{i}</link></item>'

    rss = f"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
{items_xml}
</channel></rss>"""

    parsed = feedparser.parse(rss)

    # Without isin/holding_name: cap is MARKET_FEED_CAP (25)
    items = news.normalize_entries(parsed, "India", None, None)
    assert len(items) == 25

    # With isin: cap is HOLDING_FEED_CAP (10)
    items_with_isin = news.normalize_entries(parsed, "India", "INEX", None)
    assert len(items_with_isin) == 10

    # With holding_name: cap is HOLDING_FEED_CAP (10)
    items_with_name = news.normalize_entries(parsed, "India", None, "TestHolding")
    assert len(items_with_name) == 10


def test_prune_caps_at_500(tmp_path):
    """Test that prune keeps exactly 500 rows when inserted count exceeds PRUNE_KEEP."""
    fresh_time = storage.now_iso()
    rows = []
    for i in range(510):
        rows.append((f"h{i}", f"Item {i}", f"https://example.com/x{i}", None, None,
                     "India", None, None, fresh_time))

    with storage.connect(tmp_path) as con:
        con.executemany(
            """
            INSERT INTO news_items(url_hash, title, url, publisher, published_at, market,
                                    isin, holding_name, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        con.commit()

    # Verify insertion
    with storage.connect(tmp_path) as con:
        count_before = con.execute("SELECT COUNT(*) AS c FROM news_items").fetchone()["c"]
    assert count_before == 510

    # Prune should delete 10 rows
    deleted = news.prune(tmp_path)
    assert deleted == 10

    # Verify exactly 500 remain
    with storage.connect(tmp_path) as con:
        count_after = con.execute("SELECT COUNT(*) AS c FROM news_items").fetchone()["c"]
    assert count_after == 500
