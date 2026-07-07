from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path


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


def build_prompt(one_pager: str | None, snapshot: dict, today: date) -> str:
    rules = one_pager or "(No investor one-pager on file yet — keep advice generic and say so.)"
    day = f"{today.day} {today.strftime('%B %Y')}"
    return f"""You are the personal investment strategist for this portfolio's owner.
Today is {day}.

THE OWNER'S INVESTOR ONE-PAGER (treat as governing law):
{rules}

CURRENT PORTFOLIO (live values, INR):
{json.dumps(snapshot, indent=1)}

Write today's MORNING BRIEF in markdown with EXACTLY these sections:
## MARKETS OVERNIGHT — use web search for Indian & US markets since yesterday's close.
## IMPACT ON YOUR PORTFOLIO — only positions actually affected; reference qty and member.
## SUGGESTED ACTIONS — max 3, each checked against a specific one-pager rule (name it).
Direct, no fluff, no disclaimers beyond one line. All amounts in ₹ lakh/crore format."""


def generate_brief(pf, base_dir: Path) -> Path:
    exe = find_claude()
    if not exe:
        raise BriefError(
            "Claude Code CLI not found. Install: npm install -g @anthropic-ai/claude-code "
            "then run `claude` once to log in. Or: open this folder in Claude Cowork and say "
            "\"write today's brief to briefs/\".")
    one_pager_path = base_dir / "profile" / "one-pager.md"
    one_pager = one_pager_path.read_text(encoding="utf-8") if one_pager_path.exists() else None
    prompt = build_prompt(one_pager, portfolio_snapshot(pf), date.today())
    try:
        out = subprocess.run([exe, "-p", "--allowed-tools", "WebSearch"],
                             input=prompt, capture_output=True, text=True,
                             encoding="utf-8", timeout=300)
    except subprocess.TimeoutExpired:
        raise BriefError("Brief generation timed out after 5 minutes. Try again, or generate "
                         "it in Claude Cowork instead.")
    if out.returncode != 0 or not (out.stdout or "").strip():
        raise BriefError(f"Claude CLI error: {(out.stderr or 'no output').strip()[:300]} — "
                         "check you are logged in (`claude` then /login).")
    briefs = base_dir / "briefs"
    briefs.mkdir(exist_ok=True)
    path = briefs / f"{date.today().isoformat()}.md"
    path.write_text(out.stdout, encoding="utf-8")
    return path
