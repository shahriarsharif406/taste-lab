# Devpost submission text (paste into the form)

## Project name
Taste Lab

## Tagline
Qloo-grounded buyer personas, a synthetic focus group, best-fit cities and ad copy for small e-commerce brands.

## Description (English)

**Inspiration.** Small online brands selling into the US and EU can't afford focus groups, and generic AI personas are just stereotypes. We wanted personas that come from real taste data.

**What it does.** Taste Lab is an agentic tool. You enter a product (or a product-page URL). Agents then:
1. propose distinct buyer personas, each with seed artists, brands and movies;
2. ground each persona in Qloo: `/search` resolves the seeds, `/v2/insights` returns what each taste cluster loves across domains (its *taste signature*);
3. run a synthetic focus group where every persona reacts using only its Qloo signature, with purchase intent, loves and concerns, plus a moderator synthesis;
4. rank US/EU cities (Austin, Berlin, Amsterdam, ...) with Qloo place insights filtered by location;
5. write persona-specific ad copy whose hook names the Qloo signal behind it;
6. **Collab radar:** for each persona's best city, Qloo returns the partner brand, artist and venue that audience loves, and the agent proposes one concrete collaboration or event;
7. **Taste gap:** the owner names up to 3 brands they want to be compared with; Qloo shows what those brands' audience loves that none of the personas do, and which persona sits closest;
8. **30-day plan** built from the personas, cities and partners, with evidence ids, and a **What if** test that re-runs the focus group on the same Qloo data after a price or positioning change.

Every insight carries an evidence id linking to the exact Qloo entity, affinity score and query. The app shows every Qloo call it made. Reports export as printable HTML (PDF) and Markdown.

**How we built it.** Python, Streamlit, Qloo hackathon API (`GET /search`, `GET /v2/insights`), Gemini for persona/reaction/copy text, with deterministic fallbacks so the pipeline always completes. SSRF-safe product-URL loader; keys server-side only; offline test suite.

**Why Qloo.** Qloo's cross-domain taste graph is the only source of the persona signatures, city rankings and ad hooks. A plain LLM would guess.

**Challenges.** Keeping LLM output honest: personas may only use their Qloo signature, and every claim must cite an evidence id.

**What's next.** Shopify app integration, A/B-testing generated copy against real campaign results, more domains (podcasts, books).

## Built with
Python, Streamlit, Qloo API, Gemini API

## Testing instructions (for judges)
Open the demo link and click **Use example product**, then **Run Taste Lab**. No login required. (If the banner says DEMO MODE the Qloo key is not configured on the host; see the repo README.)

## Links to fill in
- Demo: <deployed URL>
- Repo (public, MIT): <GitHub URL>
- Video: <YouTube/Vimeo URL>
