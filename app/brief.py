from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

NEWS_CAP = 30
_SECTION_TOKENS = [("MARKET BRIEF", "market_brief"), ("MY STOCKS", "my_stocks"),
                   ("IMPACT NOTES", "impact_notes")]
_SIGNALS_HEADING = "FUTURE IMPACT SIGNALS"
SIGNALS = {"positive", "negative", "neutral"}


class BriefError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def find_claude() -> str | None:
    return shutil.which("claude")


def portfolio_snapshot(pf) -> dict:
    cons = pf.consolidated()
    total = pf.totals()
    return {
        "date_generated": str(date.today()),
        "total_value": round(total.total_value),
        "members": {m: round(pf.totals(m).total_value) for m in pf.members},
        "positions": [{"name": c.name, "nse": c.nse_symbol, "qty": c.qty,
                       "value": round(c.value),
                       "pl_pct": round(c.pl_pct, 1) if c.pl_pct is not None else None,
                       "day_pct": round(c.day_pct, 2) if c.day_pct is not None else None,
                       "held_by": c.held_by}
                      for c in cons[:40]],
        "extras_by_class": {k: round(v) for k, v in total.extras_by_class.items()},
        "movers": [{"name": c.name, "day_pct": round(c.day_pct, 2)} for c in pf.movers()],
    }


def _news_block(news_items: list[dict] | None) -> str:
    items = (news_items or [])[:NEWS_CAP]
    if not items:
        return "(no recent news items available)"
    lines = []
    for item in items:
        holding = item.get("holding_name") or "-"
        lines.append(f"- [{item.get('id')}] {item.get('title')} — "
                     f"{item.get('publisher') or 'Unknown'} — {item.get('url')} — "
                     f"holding:{holding}")
    return "\n".join(lines)


def build_prompt(one_pager: str | None, snapshot: dict, today: date,
                 news_items: list[dict] | None = None) -> str:
    rules = one_pager or "(No investor one-pager on file yet — keep advice generic and say so.)"
    day = f"{today.day} {today.strftime('%B %Y')}"
    news_block = _news_block(news_items)
    return f"""You are the personal investment strategist for this portfolio's owner.
Today is {day}.

THE OWNER'S INVESTOR ONE-PAGER (treat as governing law):
{rules}

CURRENT PORTFOLIO (live values, INR):
{json.dumps(snapshot, indent=1)}

NEWS (cite ONLY these urls as markdown links):
{news_block}

Write today's MORNING BRIEF in markdown with EXACTLY these sections:
## MARKET BRIEF — market-moving stories for this India-heavy book; 2-3 lines each, and a
markdown link to the source for each story, citing ONLY urls listed in the NEWS block above.
## MY STOCKS — news about held stocks; a markdown link for each item, citing ONLY urls listed
in the NEWS block above.
## IMPACT NOTES — 2-3 lines interpreting the measured day moves already present in the
CURRENT PORTFOLIO data above. Do NOT invent numbers; use ONLY the day_pct/value figures given.
## FUTURE IMPACT SIGNALS — output ONLY a JSON array in a fenced json block. Each item must be
{{"isin":"...", "name":"...", "signal":"positive|negative|neutral", "reason":"5-10 words"}}.
Use only stocks present in CURRENT PORTFOLIO and only the three signal values.
Direct, no fluff, no disclaimers beyond one line. All amounts in ₹ lakh/crore format. Cite
ONLY the urls listed in the NEWS block — never fabricate a link."""


def split_brief(md_text: str) -> dict:
    import markdown as md

    matches = list(re.finditer(r"^##\s+(.+?)\s*$", md_text, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        heading = m.group(1).strip().upper()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        body = md_text[start:end].strip()
        for token, key in _SECTION_TOKENS:
            if token in heading:
                sections[key] = md.markdown(body, extensions=["extra"])
                break
    if not sections:
        return {"single": md.markdown(md_text, extensions=["extra"])}
    return sections


def _signals_body(md_text: str) -> str:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", md_text, flags=re.MULTILINE))
    for i, m in enumerate(matches):
        if _SIGNALS_HEADING in m.group(1).strip().upper():
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
            return md_text[start:end].strip()
    return ""


def _normalise_signal(row: dict) -> dict | None:
    signal = str(row.get("signal") or row.get("future_impact") or "").strip().lower()
    if signal not in SIGNALS:
        signal = "neutral"
    isin = str(row.get("isin") or "").strip().upper()
    name = str(row.get("name") or row.get("holding") or "").strip()
    if not isin and not name:
        return None
    reason = str(row.get("reason") or "").strip()
    return {"isin": isin, "name": name, "signal": signal, "reason": reason[:160]}


def parse_future_signals(md_text: str) -> list[dict]:
    body = _signals_body(md_text)
    if not body:
        return []
    fenced = re.search(r"```(?:json)?\s*(.*?)```", body, flags=re.DOTALL | re.IGNORECASE)
    raw = fenced.group(1).strip() if fenced else body.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    rows = parsed.get("future_impact", parsed.get("signals", [])) if isinstance(parsed, dict) else parsed
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows:
        if isinstance(row, dict):
            norm = _normalise_signal(row)
            if norm:
                out.append(norm)
    return out


def signal_sidecar_path(brief_path: Path) -> Path:
    return brief_path.with_name(f"{brief_path.stem}.signals.json")


def save_future_signals(brief_path: Path, md_text: str) -> Path | None:
    signals = parse_future_signals(md_text)
    if not signals:
        return None
    path = signal_sidecar_path(brief_path)
    path.write_text(json.dumps(signals, indent=2), encoding="utf-8")
    return path


def load_future_signals(brief_path: Path) -> dict:
    path = signal_sidecar_path(brief_path)
    if not path.exists():
        return {"by_isin": {}, "by_name": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"by_isin": {}, "by_name": {}}
    rows = raw if isinstance(raw, list) else raw.get("future_impact", [])
    by_isin, by_name = {}, {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        norm = _normalise_signal(row)
        if not norm:
            continue
        if norm["isin"]:
            by_isin[norm["isin"]] = norm
        if norm["name"]:
            by_name[norm["name"].lower()] = norm
    return {"by_isin": by_isin, "by_name": by_name}


def sanitize_links(html: str, allowed) -> str:
    allowed_set = set(allowed)
    return re.sub(
        r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        lambda m: m.group(0) if m.group(1) in allowed_set else m.group(2),
        html,
    )


def impact_rows(pf, news_items: list[dict] | None) -> list[dict]:
    newest: dict[str, dict] = {}
    for item in news_items or []:
        isin = item.get("isin")
        if not isin:
            continue
        ts = item.get("published_at") or item.get("fetched_at") or ""
        cur = newest.get(isin)
        cur_ts = (cur.get("published_at") or cur.get("fetched_at") or "") if cur else ""
        if cur is None or ts > cur_ts:
            newest[isin] = item

    cons_by_isin = {c.isin: c for c in pf.consolidated()}
    rows = []
    for isin, item in newest.items():
        c = cons_by_isin.get(isin)
        if c is None or c.day_pct is None:
            continue
        value = c.value
        day_impact = value - value / (1 + c.day_pct / 100)
        rows.append({
            "isin": isin, "name": c.name, "headline": item.get("title"), "url": item.get("url"),
            "publisher": item.get("publisher"), "day_pct": c.day_pct,
            "day_impact": day_impact, "value": value,
        })
    rows.sort(key=lambda r: -abs(r["day_impact"]))
    return rows


def generate_brief(pf, base_dir: Path, data_dir: Path) -> Path:
    exe = find_claude()
    if not exe:
        raise BriefError(
            "Claude Code CLI not found. Install: npm install -g @anthropic-ai/claude-code "
            "then run `claude` once to log in. Or: open this folder in Claude Cowork and say "
            "\"write today's brief to briefs/\".")
    one_pager_path = base_dir / "profile" / "one-pager.md"
    one_pager = one_pager_path.read_text(encoding="utf-8") if one_pager_path.exists() else None
    from app import news as news_mod
    news_items = news_mod.load_items(data_dir, within_hours=48, limit=NEWS_CAP)
    prompt = build_prompt(one_pager, portfolio_snapshot(pf), date.today(), news_items)
    try:
        out = subprocess.run([exe, "-p", "--allowed-tools", "WebSearch"],
                             input=prompt, capture_output=True, text=True,
                             encoding="utf-8", timeout=300)
    except subprocess.TimeoutExpired:
        raise BriefError("Brief generation timed out after 5 minutes. Try again, or generate "
                         "it in Claude Cowork instead.")
    stdout = (out.stdout or "").strip()
    stderr = (out.stderr or "").strip()
    if out.returncode != 0:
        detail = (stderr or stdout or f"exit code {out.returncode}")[:500]
        raise BriefError("Claude CLI failed. Try `claude -p \"Say OK\"` in this folder; "
                         "if it asks for setup, run `claude` then /login. "
                         f"Details: {detail}")
    if not stdout:
        detail = stderr[:500] if stderr else "no stderr"
        raise BriefError("Claude CLI returned no output. Test it with `claude -p \"Say OK\"`; "
                         "if it asks for setup, run `claude` then /login. If it reports a "
                         f"usage limit, wait and retry. Details: {detail}")
    briefs = base_dir / "briefs"
    briefs.mkdir(exist_ok=True)
    path = briefs / f"{date.today().isoformat()}.md"
    path.write_text(stdout, encoding="utf-8")
    save_future_signals(path, stdout)
    return path
