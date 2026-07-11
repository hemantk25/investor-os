from __future__ import annotations
import os
from pathlib import Path
from flask import Flask, Response, redirect, render_template, request, url_for

from app import parser, mapping, prices, advisory
from app import portfolio as pmod
from app import view_models as vm
from app import charts
from app import watchlist as wmod
from app import holdings_ledger as hledger

BASE = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("INVESTOR_OS_DATA", str(BASE / "data")))
HOLDINGS = DATA / "holdings.xlsx"


def load_portfolio():
    if not HOLDINGS.exists() and not hledger.has_manual_holdings(DATA):
        return None
    pr = parser.parse_holdings(HOLDINGS) if HOLDINGS.exists() else hledger.empty_parse_result(DATA)
    if HOLDINGS.exists():
        pr = hledger.apply_events(pr, DATA)
    isin_map = mapping.ensure_map(DATA)
    isin_map.update(hledger.symbol_map(DATA))
    quotes = prices.fetch_quotes([isin_map.get(h.isin) for h in pr.holdings if isin_map.get(h.isin)])
    extras = pmod.load_extras(DATA / "extras.json")
    return pmod.build_portfolio(pr, isin_map, quotes, extras)


def _empty(active, page):
    return {"active": active, "page": page, "members": [], "member": None,
            "freshness": "", "empty": True}


def _member_arg():
    member = request.args.get("member") or None
    return None if member == "All" else member


def _member_form_arg():
    member = request.form.get("member") or "All"
    return "All" if member == "All" else member


def _redirect_watchlist(member=None, market="", group="", q="", category="", subcategory=""):
    params = {}
    if member and member != "All":
        params["member"] = member
    if market:
        params["market"] = market
    if group:
        params["group"] = group
    if category:
        params["category"] = category
    if subcategory:
        params["subcategory"] = subcategory
    if q:
        params["q"] = q
    return redirect(url_for("watchlist_page", **params))


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
        member = _member_arg()
        rng = request.args.get("range", "6M")
        ctx = vm.overview(pf, member, rng)
        ctx["market_metrics"] = vm.market_metrics(prices.fetch_market_quotes(vm.MARKET_METRIC_SYMBOLS))
        ctx["watchlist_preview"] = vm.watchlist_preview(DATA, member)
        ctx.update(vm.common(pf, "overview", member))
        ctx["page"] = "Overview"
        ctx["empty"] = False
        return render_template("overview.html", **ctx)

    @app.route("/holdings")
    def holdings():
        pf = load_portfolio()
        if pf is None:
            return render_template("holdings.html", **_empty("holdings", "Holdings"))
        member = _member_arg()
        ctx = vm.holdings(pf, member, request.args.get("q", ""), hledger.list_manual(DATA))
        ctx.update(vm.common(pf, "holdings", member))
        ctx["page"] = "Holdings"
        ctx["empty"] = False
        return render_template("holdings.html", **ctx)

    @app.route("/holdings/manual", methods=["POST"])
    def holdings_manual_add():
        hledger.add_manual(DATA, request.form)
        return redirect(url_for("holdings", member=request.form.get("member") or "All"))

    @app.route("/holdings/manual/<int:item_id>/edit", methods=["POST"])
    def holdings_manual_edit(item_id):
        hledger.edit_manual(DATA, item_id, request.form)
        return redirect(url_for("holdings", member=request.form.get("member") or "All"))

    @app.route("/holdings/manual/<int:item_id>/delete", methods=["POST"])
    def holdings_manual_delete(item_id):
        hledger.delete_manual(DATA, item_id)
        return redirect(url_for("holdings"))

    @app.route("/holdings/events/sell", methods=["POST"])
    def holdings_sell():
        hledger.add_sell(DATA, request.form)
        member = request.form.get("member") or "All"
        return redirect(url_for("holdings", member=member))

    @app.route("/watchlist")
    def watchlist_page():
        pf = load_portfolio()
        member = _member_arg()
        market = request.args.get("market", "")
        group = request.args.get("group", "")
        category = request.args.get("category", "")
        subcategory = request.args.get("subcategory", "")
        q = request.args.get("q", "")
        ctx = vm.watchlist_ctx(DATA, member, q, market, group, category, subcategory)
        if pf is not None:
            ctx.update(vm.common(pf, "watchlist", member))
        else:
            ctx.update(_empty("watchlist", "Watchlist"))
            ctx["empty"] = False
        ctx["page"] = "Watchlist"
        return render_template("watchlist.html", **ctx)

    @app.route("/watchlist/boards", methods=["POST"])
    def watchlist_board_add():
        wmod.create_board(DATA, request.form)
        return _redirect_watchlist(_member_form_arg(), request.form.get("market", ""))

    @app.route("/watchlist/boards/<int:board_id>/close", methods=["POST"])
    def watchlist_board_close(board_id):
        wmod.close_board(DATA, str(board_id))
        return _redirect_watchlist(request.form.get("member_filter") or "All")

    @app.route("/watchlist/items", methods=["POST"])
    def watchlist_add():
        member = _member_form_arg()
        market = request.form.get("market", "Global")
        group = request.form.get("group") or request.form.get("subcategory") or "Custom"
        category = request.form.get("category", "Custom")
        subcategory = request.form.get("subcategory", group)
        wmod.add_item(DATA, {"symbol": request.form.get("symbol", ""),
                             "name": request.form.get("name", ""),
                             "market": market, "category": category,
                             "subcategory": subcategory, "group": group,
                             "member": member,
                             "watchlist_id": request.form.get("watchlist_id")})
        return _redirect_watchlist(member, market, group, category=category, subcategory=subcategory)

    @app.route("/watchlist/items/<item_id>/delete", methods=["POST"])
    def watchlist_delete(item_id):
        wmod.delete_item(DATA, item_id)
        return _redirect_watchlist(request.form.get("member_filter") or "All",
                                   request.form.get("market_filter", ""),
                                   request.form.get("group_filter", ""),
                                   request.form.get("q_filter", ""),
                                   request.form.get("category_filter", ""),
                                   request.form.get("subcategory_filter", ""))

    @app.route("/watchlist/import", methods=["POST"])
    def watchlist_import():
        member = _member_form_arg()
        market = request.form.get("market", "Global")
        group = request.form.get("group") or request.form.get("subcategory") or "Custom"
        category = request.form.get("category", "Custom")
        subcategory = request.form.get("subcategory", group)
        watchlist_id = request.form.get("watchlist_id")
        text = request.form.get("symbols", "")
        file = request.files.get("file")
        if file and file.filename:
            text = file.read().decode("utf-8", "ignore")
        wmod.import_text(DATA, text, market, group, member, category, subcategory, watchlist_id)
        return _redirect_watchlist(member, market, group, category=category, subcategory=subcategory)

    @app.route("/watchlist/export")
    def watchlist_export():
        member = _member_arg()
        market = request.args.get("market", "")
        group = request.args.get("group", "")
        category = request.args.get("category", "")
        subcategory = request.args.get("subcategory", "")
        watchlist_id = request.args.get("watchlist_id")
        q = request.args.get("q", "")
        items = wmod.filtered(wmod.load(DATA), q=q, market=market, member=member, group=group,
                              category=category, subcategory=subcategory,
                              watchlist_id=watchlist_id)
        body = wmod.export_text(items)
        return Response(body, mimetype="text/plain",
                        headers={"Content-Disposition": "attachment; filename=watchlist.txt"})

    @app.route("/watchlist/lists", methods=["POST"])
    def watchlist_list_add():
        member = _member_form_arg()
        market = request.form.get("market", "India")
        wmod.create_watchlist(DATA, {"name": request.form.get("name", ""),
                                     "market": market, "member": member})
        return _redirect_watchlist(member, market)

    @app.route("/watchlist/lists/<int:list_id>/rename", methods=["POST"])
    def watchlist_list_rename(list_id):
        wmod.rename_watchlist(DATA, str(list_id), request.form.get("name", ""))
        wl = wmod.get_watchlist(DATA, list_id)
        return _redirect_watchlist(wl["member"] if wl else _member_form_arg(),
                                   wl["market"] if wl else "")

    @app.route("/watchlist/lists/<int:list_id>/delete", methods=["POST"])
    def watchlist_list_delete(list_id):
        wl = wmod.get_watchlist(DATA, list_id)
        wmod.delete_watchlist(DATA, str(list_id))
        return _redirect_watchlist(wl["member"] if wl else _member_form_arg(),
                                   wl["market"] if wl else "")

    @app.route("/refresh", methods=["POST"])
    def refresh_now():
        from app import refresh as refresh_mod
        refresh_mod.run_refresh(DATA, load_portfolio())
        return redirect(request.headers.get("Referer") or url_for("overview"))

    @app.route("/rebalance")
    def rebalance():
        pf = load_portfolio()
        if pf is None:
            return render_template("rebalance.html", **_empty("rebalance", "Rebalance"))
        member = _member_arg()
        common = vm.common(pf, "rebalance", member)
        advp = DATA / "advisory.xlsx"
        if not advp.exists():
            return render_template("rebalance.html", page="Rebalance", empty=False,
                                   no_adv=True, tab="exits", exits=[], buys=[],
                                   sched=[], summary="", **common)
        from datetime import date
        adv = advisory.apply_status(advisory.parse_advisory(advp), pf, DATA, date.today())
        ctx = vm.rebalance(pf, adv, request.args.get("tab", "exits"))
        ctx.update(common)
        ctx["page"] = "Rebalance"
        ctx["empty"] = False
        ctx["no_adv"] = False
        return render_template("rebalance.html", **ctx)

    @app.route("/brief")
    def brief():
        pf = load_portfolio()
        if pf is None:
            return render_template("brief.html", **_empty("brief", "Morning Brief"))
        member = _member_arg()
        ctx = vm.brief_ctx(BASE, pf, request.args.get("pick"), DATA)
        ctx.update(vm.common(pf, "brief", member))
        ctx["page"] = "Morning Brief"
        ctx["empty"] = False
        ctx["error"] = request.args.get("error", "")
        from app import brief as bmod
        ctx["claude_ok"] = bool(bmod.find_claude())
        return render_template("brief.html", **ctx)

    @app.route("/brief/generate", methods=["POST"])
    def brief_generate():
        from app import brief as bmod
        pf = load_portfolio()
        if pf is None:
            return redirect(url_for("brief"))
        try:
            bmod.generate_brief(pf, BASE, DATA)
            return redirect(url_for("brief"))
        except bmod.BriefError as e:
            return redirect(url_for("brief", error=e.message))

    @app.route("/news")
    def news_page():
        member = _member_arg()
        ctx = vm.news_ctx(DATA, request.args.get("market"), request.args.get("mine") == "1")
        pf = load_portfolio()
        ctx.update(vm.common(pf, "news", member) if pf else _empty("news", "News"))
        ctx["page"] = "News"; ctx["empty"] = False
        return render_template("news.html", **ctx)

    @app.route("/news/refresh", methods=["POST"])
    def news_refresh():
        from app import news as nmod
        nmod.fetch_all(DATA, load_portfolio())
        return redirect(url_for("news_page"))

    @app.route("/goal")
    def goal_page():
        pf = load_portfolio()
        if pf is None:
            return render_template("goal.html", **_empty("goal", "Goal"))
        member = _member_arg()
        ctx = vm.goal_ctx(pf, DATA)
        ctx.update(vm.common(pf, "goal", member))
        ctx["page"] = "Goal"
        ctx["empty"] = False
        return render_template("goal.html", **ctx)

    @app.route("/profile")
    def profile():
        pf = load_portfolio()
        member = _member_arg()
        ctx = vm.profile_ctx(BASE)
        if pf is not None:
            ctx.update(vm.common(pf, "profile", member))
        else:
            ctx.update(_empty("profile", "Investor Profile"))
            ctx["empty"] = False
        ctx["page"] = "Investor Profile"
        return render_template("profile.html", **ctx)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8555, debug=False)
