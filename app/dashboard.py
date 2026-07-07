from pathlib import Path

import streamlit as st

from app import theme

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"

st.set_page_config(page_title="Investor OS — Paresh Karia", page_icon="◈", layout="wide")
theme.inject()


def member_selector(members: list[str]) -> str | None:
    choice = st.segmented_control("Member", ["All"] + members, default="All",
                                  label_visibility="collapsed")
    return None if choice in (None, "All") else choice


def view_overview():
    st.info("Overview — coming in Task 8")


def view_holdings():
    st.info("Holdings — coming in Task 9")


def view_rebalance():
    st.info("Rebalance — coming in Task 10")


def view_brief():
    st.info("Morning Brief — coming in Task 11")


def view_profile():
    st.info("Profile — coming in Task 12")


VIEWS = {"◈ Overview": view_overview, "▤ Holdings": view_holdings,
         "⚖ Rebalance": view_rebalance, "⚡ Morning Brief": view_brief,
         "👤 Investor Profile": view_profile}

with st.sidebar:
    st.markdown('<div class="brand">INVESTOR OS</div>', unsafe_allow_html=True)
    st.caption("Private · Paresh Karia")
    view = st.radio("View", list(VIEWS), label_visibility="collapsed")

st.title("Paresh Karia — Investor OS")
VIEWS[view]()
