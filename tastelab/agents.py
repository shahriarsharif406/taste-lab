"""The Taste Lab agent pipeline.

    brief -> plan personas -> resolve seeds in Qloo -> taste signatures (Qloo insights)
          -> focus-group reactions -> moderator synthesis -> city fit (Qloo location insights)
          -> persona ad copy

Every claim carries evidence ids (Q1, Q2, ...) that point at a concrete Qloo result, so the
UI can show *why* an insight exists. If no Gemini key is set, deterministic offline text is
used; the Qloo data (live or demo) is the same either way.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from . import config, demo_data
from .llm import LLM
from .qloo_client import Entity, QlooClient, QlooError

SIGNATURE_TYPES = ["artist", "brand", "movie"]


@dataclass
class Brief:
    product_name: str
    description: str
    audience: str = ""
    price_point: str = ""
    market: str = "US + EU"
    cities: list[str] = field(default_factory=lambda: list(config.DEFAULT_CITIES))
    num_personas: int = 4
    anchors: list[str] = field(default_factory=list)


class Evidence:
    """Registry that hands out stable ids (Q1, Q2...) for Qloo results."""

    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}
        self._by_key: dict[tuple, str] = {}

    def add(self, ent: Entity, via: str, context: str = "") -> str:
        key = (ent.id, via, context)
        if key in self._by_key:
            return self._by_key[key]
        eid = f"Q{len(self.items) + 1}"
        self.items[eid] = {"id": eid, "entity": ent.name, "type": ent.type, "affinity": ent.affinity,
                           "qloo_id": ent.id, "via": via, "context": context, "demo": ent.demo}
        self._by_key[key] = eid
        return eid


# --------------------------------------------------------------------------- personas
def _as_list(x: Any) -> list[Any]:
    """LLMs sometimes return a bare string or null where a list was asked for."""
    if x is None:
        return []
    return list(x) if isinstance(x, (list, tuple)) else [x]


def _ids(items: Any, allowed: set[str]) -> list[str]:
    """Pull evidence ids (Q12) out of whatever the model returned ('Tesla [Q27]', 'Q27', ...)."""
    found: list[str] = []
    for x in _as_list(items):
        for m in re.findall(r"Q\d+", str(x)):
            if m in allowed and m not in found:
                found.append(m)
    return found


def _sig_ids(sig: dict[str, Any]) -> set[str]:
    return {r["evidence"] for rows in sig["signature"].values() for r in rows}


def _short(text: str, limit: int = 110) -> str:
    first = text.strip().split('. ')[0].rstrip('.')
    if len(first) > limit:
        first = first[:limit].rsplit(' ', 1)[0]
    words = first.split()
    while words and words[-1].lower() in {'and', 'or', 'for', 'to', 'with', 'by', 'the', 'a', 'of', 'in'}:
        words.pop()
    return ' '.join(words) + '.'


def plan_personas(brief: Brief, llm: LLM) -> list[dict[str, Any]]:
    prompt = f"""You design buyer personas for a small e-commerce brand selling to {brief.market}.
Product: {brief.product_name}
Description: {brief.description}
Target audience hint: {brief.audience or 'not specified'}
Price point: {brief.price_point or 'not specified'}
Brands the owner wants to be compared with: {', '.join(brief.anchors) or 'none given'}

Return JSON: {{"personas": [{{"name": str, "tagline": str, "seeds": [{{"name": str, "type": "artist"|"brand"|"movie"}}]}}]}}
Create {brief.num_personas} genuinely different personas: different life stages, motivations, budgets and attitudes to this kind of product (include at least one sceptical or price-sensitive buyer, and not only the obvious target customer). Each has 3 seeds: one artist, one brand and one movie that this persona genuinely loves.
Seeds are looked up in a taste-graph API by name, so use only globally famous, unambiguous names that are popular in the US and Europe:
the full official title for films (never a bare generic word like "Office"), and the exact well-known name for artists and brands."""
    data = llm.json(prompt, system="You are a precise consumer-insights strategist. Output JSON only.")
    personas: list[dict[str, Any]] = []
    raw = data.get("personas") if isinstance(data, dict) else data
    for p in (raw if isinstance(raw, list) else []):
        if not isinstance(p, dict) or len(personas) >= brief.num_personas:
            continue
        seeds = []
        for s_ in _as_list(p.get("seeds")):
            if isinstance(s_, dict):
                n_, t_ = s_.get("name"), str(s_.get("type", "")).lower()
            elif isinstance(s_, (list, tuple)) and len(s_) == 2:
                n_, t_ = s_[0], str(s_[1]).lower()
            else:
                continue
            if n_ and t_ in SIGNATURE_TYPES:
                seeds.append((str(n_), t_))
        if p.get("name") and seeds:
            personas.append({"name": str(p["name"]), "tagline": str(p.get("tagline", "")), "seeds": seeds})
    if len(personas) < min(2, brief.num_personas):
        personas = [dict(a, seeds=list(a["seeds"])) for a in demo_data.ARCHETYPES[: brief.num_personas]]
    return personas


def build_signature(client: QlooClient, ev: Evidence, persona: dict[str, Any]) -> dict[str, Any]:
    """Resolve the persona's seeds, then ask Qloo what else this taste cluster loves."""
    resolved: list[Entity] = []
    for name, etype in persona["seeds"]:
        hits = client.search(name, etype, take=1)
        if hits:
            resolved.append(hits[0])
    if len(resolved) < 3:  # a seed that did not resolve leaves the signature thin; top up with famous US/EU names
        have = {e.type for e in resolved}
        used = {e.name.lower() for e in resolved}
        for t in SIGNATURE_TYPES:
            if len(resolved) >= 3:
                break
            if t in have:
                continue
            pool = sorted(demo_data.POOL[t], key=lambda n: demo_data.stable_int(persona["name"], n))
            for cand in pool[:3]:
                if cand.lower() in used:
                    continue
                hits = client.search(cand, t, take=1)
                if hits:
                    resolved.append(hits[0])
                    used.add(hits[0].name.lower())
                    break
    seed_ids = [e.id for e in resolved]
    seed_refs = [{"entity": e.name, "type": e.type, "evidence": ev.add(e, "search", f"seed for {persona['name']}")}
                 for e in resolved]
    signature: dict[str, list[dict[str, Any]]] = {}
    for t in SIGNATURE_TYPES:
        rows = []
        seen: set[str] = set()
        for ent in client.insights(t, seed_ids, take=6):
            if ent.name.lower() in seen or len(rows) >= 5:  # Qloo can return two entities with one name
                continue
            seen.add(ent.name.lower())
            rows.append({"name": ent.name, "affinity": ent.affinity,
                         "evidence": ev.add(ent, "insights", f"{t} affinity for {persona['name']}")})
        signature[t] = rows
    return {"seeds": seed_refs, "seed_ids": seed_ids, "signature": signature}


# --------------------------------------------------------------------------- focus group
def _sig_text(sig: dict[str, Any]) -> str:
    lines = []
    for t, rows in sig["signature"].items():
        if rows:
            lines.append(f"{t}: " + ", ".join(f"{r['name']} [{r['evidence']}]" for r in rows))
    return "\n".join(lines)


def react(brief: Brief, persona: dict[str, Any], sig: dict[str, Any], llm: LLM) -> dict[str, Any]:
    prompt = f"""Persona: {persona['name']} - {persona['tagline']}
Verified taste signature from Qloo (evidence ids in brackets):
{_sig_text(sig)}

Product: {brief.product_name} - {brief.description} (price: {brief.price_point or 'n/a'}; market: {brief.market})

React in first person as this persona, as a realistic and critical consumer: be honest about what does not fit, and spread scores to reflect how well this product really suits THIS persona (a poor fit should score 3-5, a strong fit 8-9; avoid giving everyone the same score). Ground every point in the taste signature and cite evidence ids like Q12.
Return JSON: {{"reaction": str (2-3 sentences), "score": int 1-10 (purchase intent), "loves": [str], "concerns": [str], "evidence": [str]}}"""
    data = llm.json(prompt, system="You simulate consumers faithfully; never invent facts beyond the signature.")
    all_ev = [r["evidence"] for rows in sig["signature"].values() for r in rows]
    if isinstance(data, dict) and data.get("reaction"):
        try:
            score = max(1, min(10, int(data.get("score", 6))))
        except (TypeError, ValueError):
            score = 6
        return {"reaction": str(data["reaction"]), "score": score,
                "loves": [str(x) for x in _as_list(data.get("loves"))][:4],
                "concerns": [str(x) for x in _as_list(data.get("concerns"))][:4],
                "evidence": _ids(data.get("evidence"), set(all_ev)) or all_ev[:3]}
    # offline fallback: deterministic, derived from real affinity numbers
    affs = [r["affinity"] for rows in sig["signature"].values() for r in rows if r["affinity"] is not None]
    avg = mean(affs) if affs else 0.6
    score = max(3, min(9, round(avg * 10) - 1 + demo_data.stable_int(persona["name"], brief.product_name) % 2))
    top = [r for rows in sig["signature"].values() for r in rows][:2]
    anchors = " and ".join(f"{r['name']}" for r in top) or "my usual favourites"
    return {
        "reaction": (f"As someone whose taste runs through {anchors}, {brief.product_name} feels "
                     f"{'like a natural fit' if score >= 7 else 'interesting but not yet a must-have'}. "
                     "I would want the story and design to match what I already follow."),
        "score": int(score),
        "loves": [f"Fits the {persona['name'].lower().removeprefix('the ')} mindset", "Clear, honest positioning"],
        "concerns": ["Needs proof of quality or values", "Price should feel justified"],
        "evidence": [r["evidence"] for r in top] or all_ev[:2],
    }


def moderate(brief: Brief, results: list[dict[str, Any]], llm: LLM) -> str:
    summary = "\n".join(f"- {r['persona']['name']}: score {r['reaction']['score']}/10. {r['reaction']['reaction']}"
                        for r in results)
    data = llm.json(
        f"""You moderate a synthetic focus group for {brief.product_name}.
{summary}
Return JSON: {{"synthesis": str}} - 3-4 sentences: where personas agree, where they genuinely differ (name the personas and scores), and the single
positioning angle that works best across them. Do not claim agreement the scores do not support.""")
    if isinstance(data, dict) and data.get("synthesis"):
        return str(data["synthesis"])
    best = max(results, key=lambda r: r["reaction"]["score"])
    worst = min(results, key=lambda r: r["reaction"]["score"])
    return (f"Strongest pull comes from {best['persona']['name']} ({best['reaction']['score']}/10); "
            f"{worst['persona']['name']} is the hardest sell ({worst['reaction']['score']}/10). "
            "Lead with the angle the top persona already loves, and answer the concerns of the weakest one "
            "before spending on that segment.")


# --------------------------------------------------------------------------- city fit
def _places(client: QlooClient, seed_ids: list[str], city: str) -> list[Entity]:
    try:
        return client.insights("place", seed_ids, location=city, take=8)
    except QlooError:
        return []


def _mean_aff(places: list[Entity]) -> float:
    affs = [p.affinity for p in places if p.affinity is not None]
    return round(mean(affs) * 100, 1) if affs else 0.0


def city_fit(client: QlooClient, ev: Evidence, brief: Brief, seed_ids: list[str],
             persona_seeds: list[tuple[str, list[str]]] | None = None) -> list[dict[str, Any]]:
    """Rank cities. Overall score uses all personas' seeds together; ``by_persona`` scores each
    persona's own seeds separately, so different audiences can favour different cities."""
    from concurrent.futures import ThreadPoolExecutor

    persona_seeds = persona_seeds or []
    jobs: list[tuple[str | None, str, list[str]]] = [(None, c, seed_ids) for c in brief.cities]
    jobs += [(name, c, ids) for name, ids in persona_seeds for c in brief.cities]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda j: _places(client, j[2], j[1]), jobs))

    rows: dict[str, dict[str, Any]] = {}
    for (name, city, _), places in zip(jobs, results):
        row = rows.setdefault(city, {"city": city, "score": 0.0, "top_places": [], "by_persona": {}})
        if name is None:  # overall (evidence is added sequentially, so ids stay deterministic)
            row["score"] = _mean_aff(places)
            row["top_places"] = [{"name": p.name, "affinity": p.affinity,
                                  "evidence": ev.add(p, "insights", f"place affinity in {city}")}
                                 for p in places[:3]]
        else:
            row["by_persona"][name] = _mean_aff(places)
    out = sorted(rows.values(), key=lambda r: r["score"], reverse=True)
    avg = mean(r["score"] for r in out) if out else 0.0
    for r in out:
        r["vs_avg"] = round(r["score"] - avg, 1)
    return out


# --------------------------------------------------------------------------- ad copy
def ad_copy(brief: Brief, persona: dict[str, Any], sig: dict[str, Any], reaction: dict[str, Any],
            llm: LLM) -> dict[str, Any]:
    prompt = f"""Write ad copy for {brief.product_name} ({brief.description}) aimed at: {persona['name']} - {persona['tagline']}.
Taste signature from Qloo:
{_sig_text(sig)}
Their concerns: {reaction['concerns']}
Return JSON: {{"headline": str (<=8 words), "body": str (<=35 words), "cta": str, "hook_reason": str, "evidence": [str]}}.
The hook must reference a taste signal by name. Put the evidence id (like Q12) only in "evidence" and "hook_reason", never inside headline, body or cta.
Rules: only claim features stated in the product description (do not invent features such as modular organisation); never mention a competitor
or send the reader to another brand, the CTA must lead to {brief.product_name}; no fake claims or testimonials."""
    data = llm.json(prompt, system="You are a direct-response copywriter who never fabricates claims.")
    if isinstance(data, dict) and data.get("headline"):
        out = {k: str(data.get(k, "")) for k in ("headline", "body", "cta", "hook_reason")}
        allowed = _sig_ids(sig)
        # models sometimes leave the evidence list empty but cite ids in the text; use those
        out["evidence"] = (_ids(data.get("evidence"), allowed)
                           or _ids([out["hook_reason"], out["body"], out["headline"], out["cta"]], allowed))
        for k in ("headline", "body", "cta"):  # ad text a customer sees must not carry [Q12] markers
            out[k] = re.sub(r"\s*\[Q\d+(?:\s*,\s*Q\d+)*\]", "", out[k]).strip()
        return out
    top = next((r for rows in sig["signature"].values() for r in rows), None)
    anchor = top["name"] if top else "what you love"
    return {
        "headline": f"{brief.product_name}, made for {persona['name'].replace('The ', '').lower()}s",
        "body": f"If you are into {anchor}, you will notice the details. {_short(brief.description)}",
        "cta": "Take a closer look",
        "hook_reason": f"Opens with {anchor}, a high-affinity signal for this persona.",
        "evidence": [top["evidence"]] if top else [],
    }


# --------------------------------------------------------------------------- anchors + taste gap
def resolve_anchors(client: QlooClient, ev: Evidence, names: list[str]) -> list[tuple[Entity, str]]:
    """Look up the brands the owner wants to be compared with (max 3). Failures are skipped."""
    out: list[tuple[Entity, str]] = []
    for n in names[:3]:
        try:
            hits = client.search(n, "brand", take=1)
        except QlooError:
            continue
        if hits:
            out.append((hits[0], ev.add(hits[0], "search", "anchor brand")))
    return out


def taste_gap(client: QlooClient, ev: Evidence, anchors: list[tuple[Entity, str]],
              results: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Compare what the anchor brands' audience loves with what our personas love."""
    if not anchors:
        return None
    ids = [a.id for a, _ in anchors]
    rows: list[dict[str, Any]] = []
    for t in SIGNATURE_TYPES:
        try:
            ents = client.insights(t, ids, take=8)
        except QlooError:
            ents = []
        for ent in ents:
            rows.append({"name": ent.name, "type": t, "affinity": ent.affinity,
                         "evidence": ev.add(ent, "insights", f"{t} affinity for anchor brands")})

    def names(r: dict[str, Any]) -> set[str]:
        return {x["name"].lower() for rs in r["signature"]["signature"].values() for x in rs}

    persona_names = {r["persona"]["name"]: names(r) for r in results}
    everyone = set().union(*persona_names.values()) if persona_names else set()
    shared = [x for x in rows if x["name"].lower() in everyone]
    missing = sorted((x for x in rows if x["name"].lower() not in everyone),
                     key=lambda x: x["affinity"] or 0, reverse=True)[:6]
    match = {n: round(100 * sum(1 for x in rows if x["name"].lower() in ns) / len(rows)) if rows else 0
             for n, ns in persona_names.items()}
    return {"anchors": [{"name": a.name, "evidence": i} for a, i in anchors],
            "shared": shared[:8], "missing": missing, "match": match}


# --------------------------------------------------------------------------- collab radar
def radar_base(client: QlooClient, ev: Evidence, brief: Brief, results: list[dict[str, Any]],
               cities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """For every persona: the best partner brand, artist and venue (all straight from Qloo)."""
    out = []
    for r in results:
        name = r["persona"]["name"]
        sig = r["signature"]["signature"]
        city = max(cities, key=lambda c: c["by_persona"].get(name, 0))["city"] if cities else None
        places = _places(client, r["signature"]["seed_ids"], city)[:3] if city else []
        venues = [{"name": p.name, "affinity": p.affinity,
                   "evidence": ev.add(p, "insights", f"place affinity in {city}")} for p in places]
        brands = [x for x in sig.get("brand", []) if x["name"].lower() != brief.product_name.lower()]
        out.append({"persona": name, "city": city, "brand": brands[0] if brands else None,
                    "artist": (sig.get("artist") or [None])[0], "venue": venues[0] if venues else None,
                    "venues": venues})
    return out


def radar_idea(brief: Brief, row: dict[str, Any], llm: LLM) -> dict[str, Any]:
    parts = {k: row[k] for k in ("brand", "artist", "venue") if row.get(k)}
    allowed = {v["evidence"] for v in parts.values()}
    desc = "; ".join(f"{k}: {v['name']} [{v['evidence']}]" for k, v in parts.items())
    data = llm.json(
        f"""Product: {brief.product_name} - {brief.description}
Audience: {row['persona']}. Best city: {row['city']}.
Qloo says this audience's taste points to: {desc}
Return JSON: {{"idea": str (max 40 words: one concrete collaboration or event idea using these partners),
"evidence": [str]}}. Use only partners from the list that genuinely fit this product and audience (at most two or three; skip any
that make no sense for it, such as an unrelated fashion or airline brand). Do not invent facts about them.""",
        system="You are a brand partnerships strategist. Output JSON only.") if parts else None
    if isinstance(data, dict) and data.get("idea"):
        return {"idea": str(data["idea"]), "evidence": _ids(data.get("evidence"), allowed) or sorted(allowed)}
    bits = []
    if row.get("brand"):
        bits.append(f"a limited drop with {row['brand']['name']}")
    if row.get("artist"):
        bits.append(f"a listening night curated around {row['artist']['name']}")
    where = f" at {row['venue']['name']}" if row.get("venue") else ""
    city = f" in {row['city']}" if row.get("city") else ""
    idea = ("Try " + " and ".join(bits) + where + city + ".") if bits else "No partner signals were returned."
    return {"idea": idea, "evidence": sorted(allowed)}


# --------------------------------------------------------------------------- launch playbook
def playbook(brief: Brief, results: list[dict[str, Any]], radar: list[dict[str, Any]],
             allowed: set[str], llm: LLM) -> list[dict[str, Any]]:
    ranked = sorted(results, key=lambda r: r["reaction"]["score"], reverse=True)
    top, weak = ranked[0], ranked[-1]
    by_name = {x["persona"]: x for x in radar}
    ctx = []
    for r in ranked:
        x = by_name.get(r["persona"]["name"], {})
        ctx.append(f"- {r['persona']['name']} (intent {r['reaction']['score']}/10, concerns: "
                   f"{'; '.join(r['reaction']['concerns'][:2])}); best city {x.get('city')}; "
                   f"ad hook: {r['ad']['headline']}; partners: "
                   + ", ".join(f"{x[k]['name']} [{x[k]['evidence']}]" for k in ("brand", "artist", "venue") if x.get(k)))
    data = llm.json(
        f"""Plan the first 30 days of launching {brief.product_name} ({brief.price_point or 'price n/a'}) for a small brand.
{chr(10).join(ctx)}
Return JSON: {{"steps": [{{"when": str, "action": str (max 30 words, concrete), "evidence": [str]}}]}} with exactly 4 steps
(Week 1..Week 4). Lead with the strongest persona, test the partners above, and use week 4 to address the weakest persona's biggest
concern and re-measure. Cite evidence ids like Q12 for taste-based choices. No invented numbers.""",
        system="You are a pragmatic go-to-market strategist. Output JSON only.")
    steps: list[dict[str, Any]] = []
    if isinstance(data, dict):
        for st in _as_list(data.get("steps")):
            if isinstance(st, dict) and st.get("action"):
                steps.append({"when": str(st.get("when", f"Week {len(steps) + 1}")), "action": str(st["action"]),
                              "evidence": _ids(st.get("evidence"), allowed) or _ids([st["action"]], allowed)})
    if len(steps) >= 3:
        return steps[:4]
    tx, wx = by_name.get(top["persona"]["name"], {}), by_name.get(weak["persona"]["name"], {})
    c1 = (tx.get("city") or "your best city")
    ref = [x["evidence"] for x in (tx.get("brand"), tx.get("artist")) if x]
    steps = [
        {"when": "Week 1", "action": f"Run \"{top['ad']['headline']}\" to {top['persona']['name']} in {c1}.",
         "evidence": top["ad"]["evidence"]},
        {"when": "Week 2", "action": "Approach the suggested partner brand with a small co-branded drop"
         + (f" ({tx['brand']['name']})." if tx.get("brand") else "."),
         "evidence": [tx["brand"]["evidence"]] if tx.get("brand") else ref},
        {"when": "Week 3", "action": "Host one small event" + (f" at {tx['venue']['name']}." if tx.get("venue") else "."),
         "evidence": [tx["venue"]["evidence"]] if tx.get("venue") else []},
        {"when": "Week 4", "action": f"Address '{(weak['reaction']['concerns'] or ['their main concern'])[0]}' for "
         f"{weak['persona']['name']}, then compare results by persona.", "evidence": weak["reaction"]["evidence"][:2]},
    ]
    return steps


# --------------------------------------------------------------------------- what-if
def what_if(run: dict[str, Any], llm: LLM, price: str = "", positioning: str = "", name: str = "") -> list[dict[str, Any]]:
    """Re-run the focus group with one change; reuses the stored Qloo signatures (no new Qloo calls)."""
    from concurrent.futures import ThreadPoolExecutor
    from dataclasses import replace

    base = Brief(**run["brief"])
    new = replace(base, price_point=price.strip() or base.price_point,
                  product_name=name.strip() or base.product_name,
                  description=(base.description + " Positioning: " + positioning.strip()) if positioning.strip()
                  else base.description)
    if llm.available:
        llm.candidates()
    with ThreadPoolExecutor(max_workers=6) as pool:
        after = list(pool.map(lambda r: react(new, r["persona"], r["signature"], llm), run["personas"]))
    return [{"persona": r["persona"]["name"], "before": r["reaction"]["score"], "after": a["score"],
             "delta": a["score"] - r["reaction"]["score"], "reaction": a["reaction"], "concerns": a["concerns"]}
            for r, a in zip(run["personas"], after)]


# --------------------------------------------------------------------------- orchestrator
def run_taste_lab(brief: Brief, client: QlooClient, llm: LLM, progress=None) -> dict[str, Any]:
    def tick(msg: str) -> None:
        if progress:
            progress(msg)

    ev = Evidence()
    anchors = resolve_anchors(client, ev, brief.anchors) if brief.anchors else []
    tick("Designing personas")
    personas = plan_personas(brief, llm)

    from concurrent.futures import ThreadPoolExecutor

    if llm.available:
        llm.candidates()  # discover models once, before threads start

    sigs = []
    for p in personas:  # Qloo calls stay sequential so evidence ids are deterministic
        tick(f"Querying Qloo for {p['name']}")
        sigs.append(build_signature(client, ev, p))

    tick("Focus group reacting (parallel)")
    with ThreadPoolExecutor(max_workers=6) as pool:
        reactions = list(pool.map(lambda ps: react(brief, ps[0], ps[1], llm), zip(personas, sigs)))
        results: list[dict[str, Any]] = [{"persona": p, "signature": sg, "reaction": rx}
                                         for p, sg, rx in zip(personas, sigs, reactions)]

        tick("Writing ad copy and synthesis while ranking cities")
        ad_futs = [pool.submit(ad_copy, brief, r["persona"], r["signature"], r["reaction"], llm) for r in results]
        syn_fut = pool.submit(moderate, brief, results, llm)

        union_ids = list(dict.fromkeys(i for r in results for i in r["signature"]["seed_ids"]))
        cities = city_fit(client, ev, brief, union_ids,
                          [(r['persona']['name'], r['signature']['seed_ids']) for r in results])
        for r, f in zip(results, ad_futs):
            r["ad"] = f.result()
        synthesis = syn_fut.result()

        tick("Finding collaboration partners and the taste gap")
        radar = radar_base(client, ev, brief, results, cities)
        idea_futs = [pool.submit(radar_idea, brief, row, llm) for row in radar]
        allowed = set(ev.items)
        pb_fut = pool.submit(playbook, brief, results, radar, allowed, llm)
        gap = taste_gap(client, ev, anchors, results)
        for row, f in zip(radar, idea_futs):
            row.update(f.result())
        plan = pb_fut.result()

    return {
        "brief": brief.__dict__,
        "mode": client.mode,
        "llm": "gemini" if llm.available else "offline-fallback",
        "personas": results,
        "synthesis": synthesis,
        "cities": cities,
        "radar": radar,
        "gap": gap,
        "playbook": plan,
        "evidence": ev.items,
        "trace": client.trace,
        "warnings": list(llm.warnings),
    }
