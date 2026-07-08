from __future__ import annotations
import os
from pathlib import Path
from flask import Flask, render_template, request

BASE = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("INVESTOR_OS_DATA", str(BASE / "data")))


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.route("/health")
    def health():
        return "ok"

    @app.route("/")
    def overview():
        return render_template("base.html", active="overview", page="Overview",
                               members=[], member=None, freshness="", body="Overview coming soon")

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
