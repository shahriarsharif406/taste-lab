# 🧪 Taste Lab

**A Qloo-powered agent that tells small e-commerce brands who will love their product, in which city, what those buyers would say, and which ad hook to use. Every insight cites the Qloo result behind it.**

Built for the [Qloo Agentic Hackathon](https://qloo.devpost.com).

## The problem

Small online brands selling into the US and EU cannot afford focus groups or agency research. A generic LLM can invent personas, but it guesses. Taste Lab grounds each persona in Qloo's taste graph, so the personas, city ranking and ad hooks come from real affinity data, not stereotypes.

## What it does

1. **Input:** a product (or a public product-page URL) and optional audience / price.
2. **Persona planner (LLM agent):** proposes distinct buyer archetypes, each with seed artists, brands and movies.
3. **Qloo grounding:** seeds are resolved with `GET /search`; then `GET /v2/insights` returns what else each taste cluster loves (artists, brands, movies). This is the persona's *taste signature*.
4. **Synthetic focus group:** each persona reacts to the product using only its signature, with a purchase-intent score, loves and concerns. A moderator synthesises agreement and disagreement.
5. **City Fit Score:** `GET /v2/insights` with `filter.type=urn:entity:place` and `filter.location.query=<city>` for Austin, Berlin, Amsterdam, etc. Cities are ranked by mean affinity of the places returned.
6. **Persona-specific ad copy:** headline, body, CTA and *why this hook*, tied to a named Qloo signal.
7. **Transparency:** every claim carries an evidence id (`Q7`) that maps to a Qloo entity, affinity score and the query that fetched it. The UI also lists every Qloo call (endpoint, params, status, latency).
8. **Collab radar:** per persona and best city, `GET /v2/insights` for place, plus the brand and artist signatures, give a partner brand, artist and venue; the agent writes one concrete collaboration idea.
9. **Anchor brands and taste gap:** up to 3 brands the owner wants to be compared with are resolved in Qloo; their audience's taste is compared with each persona's (closest persona, shared taste, taste gap).
10. **30-day plan and What if:** an evidence-cited launch plan, and a re-run of the focus group with a changed price or positioning, reusing the stored Qloo data.
11. **Export:** printable HTML report (save as PDF), Markdown, and CSV of ad copy.

**Why Qloo matters here:** persona taste signatures, city rankings and ad hooks all come from Qloo affinity data. Remove Qloo and the app has nothing to ground on.

## Agent architecture

```
Brief ─► Persona planner (LLM) ─► Qloo /search (resolve seeds)
                                      │
                                      ▼
                         Qloo /v2/insights (artist, brand, movie)  = taste signature
                                      │
              ┌───────────────────────┼────────────────────────┐
              ▼                       ▼                        ▼
      Focus-group agent        City-fit agent           Ad-copy agent
      (LLM, cites Qloo ids)    (Qloo place insights     (LLM, cites Qloo ids)
              │                 per city)                       │
              └──────────────► Moderator ◄──────────────────────┘
                                      ▼
                       Report + evidence table + call trace
```

## Run it

```bash
git clone <this repo> && cd taste-lab
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add QLOO_API_KEY and GEMINI_API_KEY
streamlit run app.py
```

- With `QLOO_API_KEY` set the app uses **live Qloo data** (`https://hackathon.api.qloo.com`).
- Without it the app runs in a clearly-labelled **DEMO MODE** on synthetic fixtures (a banner is shown and reports are stamped). Demo data is **not** Qloo data.
- Without `GEMINI_API_KEY` the text parts use deterministic offline templates; Qloo data is the same.
- Verify the live integration once your key arrives: `python scripts/smoke_live.py`.

Deploy on Streamlit Community Cloud: point it at `app.py` and add `QLOO_API_KEY` / `GEMINI_API_KEY` under *Secrets*. Keys stay server-side and are only sent in request headers.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The suite runs offline: it checks the Qloo request shapes and parsing against a mocked session, 429 retry, that the key never appears in errors or reprs, LLM-failure fallbacks, the full pipeline, and SSRF protection for the product-URL loader.

## Security & privacy

- API keys come from environment variables only; never logged, never in the browser.
- The product-URL loader refuses non-http(s) URLs and private / loopback / link-local addresses.
- Only aggregate taste data is used. No personal data about individuals is collected or stored.

## Project layout

```
app.py                  Streamlit UI
tastelab/qloo_client.py Qloo client (live + demo), call trace
tastelab/agents.py      persona / focus-group / city-fit / ad-copy pipeline
tastelab/llm.py         Gemini wrapper with offline fallback
tastelab/shopify.py     product page -> brief (SSRF-safe)
tastelab/report.py      Markdown / HTML export
tests/                  offline test suite
```

## License

MIT. See [LICENSE](LICENSE).
