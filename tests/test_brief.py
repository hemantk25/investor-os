from datetime import date
from pathlib import Path

import pytest

import app.brief as brief
from app.brief import build_prompt, find_claude, portfolio_snapshot
from app.parser import parse_holdings
from app.portfolio import build_portfolio
from app.prices import Quote

FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"


def _pf():
    return build_portfolio(parse_holdings(FIX),
                           {"INE001A01001": "ALPHAMOT"}, {"ALPHAMOT": Quote(300.0, 2.0)}, [])


NEWS_ITEM = {"id": 1, "title": "Alpha Motors rallies on strong earnings",
             "url": "https://example.com/alpha-rallies", "publisher": "Mint",
             "published_at": None, "fetched_at": "2026-07-10T08:00:00",
             "market": "India", "isin": "INE001A01001", "holding_name": "Alpha Motors"}


def test_snapshot_compact_and_serialisable():
    import json
    snap = portfolio_snapshot(_pf())
    s = json.dumps(snap)
    assert "ALPHA" in s.upper() and snap["total_value"] > 0
    assert set(snap) == {"date_generated", "total_value", "members", "positions",
                         "extras_by_class", "movers"}


def test_prompt_contains_rules_and_sections():
    p = build_prompt("MY ONE PAGER RULES", portfolio_snapshot(_pf()), date(2026, 7, 8), [])
    assert "MY ONE PAGER RULES" in p
    assert "## MARKET BRIEF" in p
    assert "## FUTURE IMPACT SIGNALS" in p
    assert "## MY STOCKS" not in p
    assert "## IMPACT NOTES" not in p
    assert "8 July 2026" in p


def test_prompt_includes_news_and_contract():
    p = build_prompt("MY ONE PAGER RULES", portfolio_snapshot(_pf()), date(2026, 7, 8), [NEWS_ITEM])
    assert "## MARKET BRIEF" in p
    assert "## FUTURE IMPACT SIGNALS" in p
    assert "Do NOT write MY STOCKS or IMPACT NOTES" in p
    assert "positive|negative|neutral" in p
    assert NEWS_ITEM["url"] in p
    assert "ONLY" in p


def test_find_claude_missing(monkeypatch):
    monkeypatch.setattr(brief.shutil, "which", lambda _: None)
    assert find_claude() is None


def test_generate_brief_empty_stdout_has_diagnostic(tmp_path, monkeypatch):
    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(brief, "find_claude", lambda: "claude")
    monkeypatch.setattr(brief.subprocess, "run", lambda *args, **kwargs: Result())

    with pytest.raises(brief.BriefError) as exc:
        brief.generate_brief(_pf(), tmp_path, tmp_path)

    assert 'claude -p "Say OK"' in exc.value.message
    assert "returned no output" in exc.value.message


def test_split_brief_three_sections():
    md_text = (
        "## MARKET BRIEF\n"
        "Nifty up 0.5% on strong FII flows. [Mint](https://example.com/a)\n\n"
        "## MY STOCKS\n"
        "Alpha Motors rallied. [Mint](https://example.com/alpha-rallies)\n\n"
        "## IMPACT NOTES\n"
        "Your Alpha position gained roughly in line with the move.\n"
    )
    sections = brief.split_brief(md_text)
    assert set(sections) == {"market_brief", "my_stocks", "impact_notes"}
    assert "Nifty" in sections["market_brief"]
    assert "Alpha Motors" in sections["my_stocks"]
    assert "gained" in sections["impact_notes"]


def test_parse_and_load_future_signals(tmp_path):
    md_text = (
        "## MARKET BRIEF\nMarkets.\n\n"
        "## MY STOCKS\nAlpha.\n\n"
        "## IMPACT NOTES\nMeasured impact.\n\n"
        "## FUTURE IMPACT SIGNALS\n"
        "```json\n"
        "[{\"isin\":\"INE001A01001\",\"name\":\"Alpha Motors\",\"signal\":\"positive\",\"reason\":\"earnings momentum may continue\"}]\n"
        "```\n"
    )
    signals = brief.parse_future_signals(md_text)
    assert signals[0]["signal"] == "positive"
    path = tmp_path / "2026-07-11.md"
    path.write_text(md_text, encoding="utf-8")
    assert brief.save_future_signals(path, md_text)
    loaded = brief.load_future_signals(path)
    assert loaded["by_isin"]["INE001A01001"]["reason"] == "earnings momentum may continue"


def test_split_brief_legacy():
    md_text = "## MARKETS OVERNIGHT\nOld style brief.\n\n## SUGGESTED ACTIONS\nDo nothing.\n"
    sections = brief.split_brief(md_text)
    assert set(sections) == {"single"}
    assert "Old style brief" in sections["single"]


def test_sanitize_links_strips_unknown():
    html = ('<p><a href="https://example.com/a">Allowed link</a> and '
            '<a href="https://evil.example/b">Fabricated link</a></p>')
    out = brief.sanitize_links(html, {"https://example.com/a"})
    assert '<a href="https://example.com/a"' in out
    assert "Allowed link" in out
    assert "Fabricated link" in out
    assert "evil.example" not in out


def test_impact_rows():
    pf = _pf()
    rows = brief.impact_rows(pf, [NEWS_ITEM])
    assert len(rows) == 1
    row = rows[0]
    c = next(c for c in pf.consolidated() if c.isin == "INE001A01001")
    assert row["day_pct"] == 2.0
    assert row["day_impact"] == c.value - c.value / (1 + c.day_pct / 100)
    assert row["value"] == c.value
    assert row["isin"] == "INE001A01001"
    assert row["url"] == NEWS_ITEM["url"]
    assert row["headline"] == NEWS_ITEM["title"]
    assert row["publisher"] == NEWS_ITEM["publisher"]
