"""Taste Lab: Streamlit UI.  Run:  streamlit run app.py"""

from __future__ import annotations

import os

import streamlit as st

from tastelab import config
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

st.set_page_config(page_title="Taste Lab", page_icon="🧪", layout="wide")
st.title("🧪 Taste Lab")
st.caption("Qloo-powered taste personas, a synthetic focus group, best-fit US/EU cities and persona-specific ad copy.")

probe = client_from_env()
if probe.mode == "demo":
    st.warning("**DEMO MODE:** no Qloo API key is configured, so results come from synthetic fixtures, "
               "not from Qloo. Set `QLOO_API_KEY` for live Qloo data.")
else:
    st.success("Live Qloo data: every insight below cites the Qloo result behind it.")

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
    if run["mode"] == "demo":
        st.info("Showing DEMO results (synthetic).")
    for w in run["warnings"][:3]:
        st.caption(f"Note: {w}")
    st.subheader("Focus-group synthesis")
    st.write(run["synthesis"])

    t1, t2, t3, t4 = st.tabs(["Personas & reactions", "City fit", "Ad copy", "Qloo evidence & trace"])
    with t1:
        for r in run["personas"]:
            p, rx = r["persona"], r["reaction"]
            with st.expander(f"{p['name']}: intent {rx['score']}/10", expanded=True):
                st.caption(p["tagline"])
                st.write(rx["reaction"])
                c1, c2 = st.columns(2)
                c1.markdown("**Loves**\n" + "\n".join(f"- {x}" for x in rx["loves"]))
                c2.markdown("**Concerns**\n" + "\n".join(f"- {x}" for x in rx["concerns"]))
                for t, rows in r["signature"]["signature"].items():
                    if rows:
                        st.markdown(f"*Qloo {t} signal:* " + ", ".join(f"{x['name']} `{x['evidence']}`" for x in rows))
    with t2:
        st.bar_chart({c["city"]: c["score"] for c in run["cities"]})
        for c in run["cities"]:
            places = ", ".join(f"{p['name']} `{p['evidence']}`" for p in c["top_places"]) or "no data returned"
            st.markdown(f"**{c['city']}: {c['score']}/100.** {places}")
    with t3:
        for r in run["personas"]:
            ad = r["ad"]
            st.markdown(f"#### {r['persona']['name']}")
            st.markdown(f"**{ad['headline']}**\n\n{ad['body']}\n\n*CTA: {ad['cta']}*")
            st.caption(f"Why this hook: {ad['hook_reason']} Evidence: {', '.join(ad['evidence']) or '-'}")
    with t4:
        st.dataframe(list(run["evidence"].values()), width="stretch")
        st.markdown("**Every Qloo call made in this run**")
        st.dataframe(run["trace"], width="stretch")

    d1, d2 = st.columns(2)
    d1.download_button("Download report (HTML, print to PDF)", to_html(run), "taste-lab-report.html", "text/html")
    d2.download_button("Download report (Markdown)", to_markdown(run), "taste-lab-report.md", "text/markdown")
else:
    st.info("Enter a product in the sidebar (or load the example) and press **Run Taste Lab**.")
