"""Taste Lab: Streamlit UI.  Run:  streamlit run app.py"""

from __future__ import annotations

import os

import streamlit as st

from tastelab import config, ui
from tastelab.agents import Brief, run_taste_lab
from tastelab.llm import llm_from_env
from tastelab.qloo_client import QlooError, client_from_env
from tastelab.report import to_html, to_markdown
from tastelab.shopify import ProductPageError, fetch_product

config.load_dotenv()
try:  # Streamlit Cloud secrets -> env (keys stay server-side)
    for k in ("QLOO_API_KEY", "QLOO_BASE_URL", "GEMINI_API_KEY", "GEMINI_MODEL", "TASTELAB_DEMO"):
        if k in st.secrets and k not in os.environ:
            os.environ[k] = str(st.secrets[k])
except Exception:  # no secrets file locally
    pass

st.set_page_config(page_title="Taste Lab", page_icon="🧪", layout="wide", initial_sidebar_state="expanded")
st.markdown(ui.style_tag(), unsafe_allow_html=True)
st.markdown(ui.hero(), unsafe_allow_html=True)

probe = client_from_env()
if probe.mode == "demo":
    st.markdown(ui.note("<b>Demo mode.</b> No Qloo API key is set, so results come from synthetic fixtures, "
                        "not from Qloo. Set <code>QLOO_API_KEY</code> for live Qloo data.", "warn"),
                unsafe_allow_html=True)
else:
    st.markdown(ui.note("<b>Live Qloo data.</b> Every insight below cites the Qloo result behind it.", "live"),
                unsafe_allow_html=True)

EXAMPLE = {
    "name": "Ridgeline Daypack",
    "desc": "A 22L recycled-nylon daypack with a laptop sleeve and weatherproof zips, designed for commuting by "
            "bike and weekend hikes.",
    "aud": "Urban professionals aged 25-40 who love the outdoors",
    "price": "USD 89",
}

with st.sidebar:
    st.header("Your product")
    url = st.text_input("Product page URL (optional)", placeholder="https://yourshop.com/products/...")
    if st.button("Load from URL") and url:
        try:
            info = fetch_product(url)
            st.session_state["name"] = info["name"]
            st.session_state["desc"] = info["description"]
            if info["price"]:
                st.session_state["price"] = info["price"]
            st.success("Loaded product details.")
        except ProductPageError as exc:
            st.error(str(exc))
    if st.button("Use example product"):
        st.session_state.update(name=EXAMPLE["name"], desc=EXAMPLE["desc"], aud=EXAMPLE["aud"], price=EXAMPLE["price"])
    name = st.text_input("Product name", key="name")
    desc = st.text_area("Description", key="desc", height=110)
    aud = st.text_input("Target audience (optional)", key="aud")
    price = st.text_input("Price point (optional)", key="price")
    market = st.selectbox("Market", ["US + EU", "US", "EU"])
    cities_text = st.text_input("Cities to compare (comma separated)", ", ".join(config.DEFAULT_CITIES))
    n = st.slider("Personas", 2, 5, 4)
    go = st.button("Run Taste Lab", type="primary", width="stretch")

if go:
    if not name.strip() or not desc.strip():
        st.error("Please enter a product name and description.")
        st.stop()
    cities = [c.strip() for c in cities_text.split(",") if c.strip()][:8] or list(config.DEFAULT_CITIES)
    brief = Brief(name.strip(), desc.strip(), aud.strip(), price.strip(), market, cities, n)
    client, llm = client_from_env(), llm_from_env()
    status = st.status("Running agents...", expanded=True)
    try:
        run = run_taste_lab(brief, client, llm, progress=lambda m: status.write(m))
        status.update(label="Done", state="complete", expanded=False)
        st.session_state["run"] = run
    except QlooError as exc:
        status.update(label="Qloo call failed", state="error")
        st.error(f"{exc}. Check your key and try again.")

run = st.session_state.get("run")
if run:
    colors = ui.persona_colors([r["persona"]["name"] for r in run["personas"]])
    if run["llm"] != "gemini":
        if config.gemini_api_key():
            msg = "Gemini key is set but the call failed, so generic templates were used. " + " ".join(run["warnings"][:1])
        else:
            msg = ("Gemini key not set: persona reactions, scores and ad copy use generic templates. "
                   "The Qloo data (signals, cities, evidence) is real.")
        st.markdown(ui.note(msg, "warn"), unsafe_allow_html=True)
    if run["llm"] == "gemini" and run["warnings"]:
        st.markdown(ui.note("Gemini was slow or busy for some steps, so those parts use generic text. "
                            "Run again for fully generated copy.", "warn"), unsafe_allow_html=True)
    for w in run["warnings"][:3]:
        st.caption(f"Note: {w}")
    st.markdown(ui.ticker([v["entity"] for v in run["evidence"].values()]), unsafe_allow_html=True)
    st.markdown(ui.verdict(run["synthesis"]), unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs(["Personas", "City fit", "Ad copy", "Qloo evidence"])
    with t1:
        cols = st.columns(2)
        for i, r in enumerate(run["personas"]):
            with cols[i % 2]:
                st.markdown(ui.plate(r, colors[r["persona"]["name"]]), unsafe_allow_html=True)
    with t2:
        st.markdown("### Best city for each persona")
        st.markdown(ui.best_city(run["cities"], colors), unsafe_allow_html=True)
        st.markdown("### All cities, ranked")
        st.markdown(ui.cities(run["cities"], colors), unsafe_allow_html=True)
        st.caption("Bars show each city's Qloo place-affinity score against the average of the compared cities. "
                   "Big cities score close together, so differences are small.")
        import pandas as pd

        matrix = pd.DataFrame({c["city"]: c["by_persona"] for c in run["cities"]})
        if not matrix.empty:
            st.dataframe(matrix.style.highlight_max(axis=1, color="#D6B4AC").format("{:.1f}"), width="stretch")
    with t3:
        cols = st.columns(2)
        for i, r in enumerate(run["personas"]):
            with cols[i % 2]:
                st.markdown(ui.ad(r, colors[r["persona"]["name"]]), unsafe_allow_html=True)
    with t4:
        st.dataframe(list(run["evidence"].values()), width="stretch")
        st.markdown("**Every Qloo call made in this run**")
        st.dataframe(run["trace"], width="stretch")

    st.markdown(ui.footer(), unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    d1.download_button("Download report (HTML, print to PDF)", to_html(run), "taste-lab-report.html", "text/html")
    d2.download_button("Download report (Markdown)", to_markdown(run), "taste-lab-report.md", "text/markdown")
else:
    st.markdown(ui.note("Enter a product in the sidebar, or load the example, then press <b>Run Taste Lab</b>."),
                unsafe_allow_html=True)
