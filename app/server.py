from __future__ import annotations
import os
from pathlib import Path
from flask import Flask, render_template, request

from app import parser, mapping, prices, advisory
from app import portfolio as pmod
from app import view_models as vm
from app import charts

BASE = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("INVESTOR_OS_DATA", str(BASE / "data")))
HOLDINGS = DATA / "holdings.xlsx"


def load_portfolio():
    if not HOLDINGS.exists():
        return None
    pr = parser.parse_holdings(HOLDINGS)
    isin_map = mapping.ensure_map(DATA)
    quotes = prices.fetch_quotes([isin_map.get(h.isin) for h in pr.holdings if isin_map.get(h.isin)])
    extras = pmod.load_extras(DATA / "extras.json")
    return pmod.build_portfolio(pr, isin_map, quotes, extras)


def _empty(active, page):
    return {"active": active, "page": page, "members": [], "member": None,
            "freshness": "", "empty": True}


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.route("/health")
    def health():
        return "ok"

    @app.route("/")
    def overview():
        pf = load_portfolio()
        if pf is None:
            return render_template("overview.html", **_empty("overview", "Overview"))
        member = request.args.get("member") or None
        member = None if member == "All" else member
        rng = request.args.get("range", "6M")
        ctx = vm.overview(pf, member, rng)
        hist = prices.fetch_history([c.nse_symbol for c in pf.consolidated(member) if c.nse_symbol],
                                    vm.RANGE_TO_PERIOD.get(rng, "6mo"))
        ctx["chart"] = charts.area_path(charts.portfolio_series(pf, member, hist))
        ctx.update(vm.common(pf, "overview", member))
        ctx["page"] = "Overview"
        ctx["empty"] = False
        return render_template("overview.html", **ctx)

    @app.route("/holdings")
    def holdings():
        return render_template("base.html", active="holdings", page="Holdings",
                               members=[], member=None, freshness="", body="Holdings coming soon")

    @app.route("/rebalance")
    def rebalance():
        return render_template("base.html", active="rebalance", page="Rebalance",
                               members=[], member=None, freshness="", body="Rebalance coming soon")

    @app.route("/brief")
    def brief():
        return render_template("base.html", active="brief", page="Morning Brief",
                               members=[], member=None, freshness="", body="Brief coming soon")

    @app.route("/profile")
    def profile():
        return render_template("base.html", active="profile", page="Investor Profile",
                               members=[], member=None, freshness="", body="Profile coming soon")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8555, debug=False)
