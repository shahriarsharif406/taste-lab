"""Render a finished Taste Lab run as Markdown or a self-contained, printable HTML report."""

from __future__ import annotations

import html
from typing import Any


def _ev_list(ids: list[str]) -> str:
    return ", ".join(ids) if ids else "-"


def to_markdown(run: dict[str, Any]) -> str:
    b = run["brief"]
    lines = [f"# Taste Lab report: {b['product_name']}", ""]
    if run["mode"] == "demo":
        lines += ["> **DEMO MODE: synthetic data, not from Qloo.**", ""]
    lines += [f"**Product:** {b['description']}", f"**Market:** {b['market']}", "",
              "## Focus-group synthesis", run["synthesis"], "", "## Best-fit cities"]
    for c in run["cities"]:
        places = "; ".join(f"{p['name']} [{p['evidence']}]" for p in c["top_places"]) or "no data"
        lines.append(f"- **{c['city']}**: {c['score']}/100 ({places})")
    lines += ["", "## Personas"]
    for r in run["personas"]:
        p, rx, ad = r["persona"], r["reaction"], r["ad"]
        lines += [f"### {p['name']} (intent {rx['score']}/10)", f"*{p['tagline']}*", "",
                  f"> {rx['reaction']}", "",
                  f"- Loves: {'; '.join(rx['loves']) or '-'}",
                  f"- Concerns: {'; '.join(rx['concerns']) or '-'}",
                  f"- Evidence: {_ev_list(rx['evidence'])}", "",
                  f"**Ad:** {ad['headline']}", f"{ad['body']}", f"*CTA: {ad['cta']}*",
                  f"Why this hook: {ad['hook_reason']} (evidence: {_ev_list(ad['evidence'])})", ""]
    lines += ["## Evidence (Qloo results behind each insight)", "",
              "| ID | Entity | Type | Affinity | Why it was fetched |", "|---|---|---|---|---|"]
    for e in run["evidence"].values():
        aff = "" if e["affinity"] is None else f"{e['affinity']:.2f}"
        lines.append(f"| {e['id']} | {e['entity']} | {e['type']} | {aff} | {e['context']} |")
    lines += ["", "_Privacy: only aggregate taste data is used; no personal data about individuals._"]
    return "\n".join(lines)


def to_html(run: dict[str, Any]) -> str:
    esc = html.escape
    b = run["brief"]
    parts = [f"<h1>Taste Lab report: {esc(b['product_name'])}</h1>"]
    if run["mode"] == "demo":
        parts.append('<p class="warn"><b>DEMO MODE:</b> synthetic data, not from Qloo.</p>')
    parts.append(f"<p>{esc(b['description'])}<br><small>Market: {esc(b['market'])}</small></p>")
    parts.append(f"<h2>Focus-group synthesis</h2><p>{esc(run['synthesis'])}</p>")
    parts.append("<h2>Best-fit cities</h2><table><tr><th>City</th><th>Score</th><th>Top Qloo places</th></tr>")
    for c in run["cities"]:
        places = "; ".join(f"{esc(p['name'])} [{esc(p['evidence'])}]" for p in c["top_places"]) or "no data"
        parts.append(f"<tr><td>{esc(c['city'])}</td><td>{c['score']}</td><td>{places}</td></tr>")
    parts.append("</table><h2>Personas</h2>")
    for r in run["personas"]:
        p, rx, ad = r["persona"], r["reaction"], r["ad"]
        parts.append(
            f"<div class='card'><h3>{esc(p['name'])} <span class='pill'>intent {rx['score']}/10</span></h3>"
            f"<em>{esc(p['tagline'])}</em><blockquote>{esc(rx['reaction'])}</blockquote>"
            f"<p><b>Loves:</b> {esc('; '.join(rx['loves']))}<br><b>Concerns:</b> {esc('; '.join(rx['concerns']))}<br>"
            f"<b>Evidence:</b> {esc(_ev_list(rx['evidence']))}</p>"
            f"<p><b>Ad:</b> {esc(ad['headline'])}<br>{esc(ad['body'])}<br><i>CTA: {esc(ad['cta'])}</i><br>"
            f"<small>Why: {esc(ad['hook_reason'])} ({esc(_ev_list(ad['evidence']))})</small></p></div>")
    parts.append("<h2>Evidence</h2><table><tr><th>ID</th><th>Entity</th><th>Type</th><th>Affinity</th><th>Context</th></tr>")
    for e in run["evidence"].values():
        aff = "" if e["affinity"] is None else f"{e['affinity']:.2f}"
        parts.append(f"<tr><td>{esc(e['id'])}</td><td>{esc(e['entity'])}</td><td>{esc(e['type'])}</td>"
                     f"<td>{aff}</td><td>{esc(e['context'])}</td></tr>")
    parts.append("</table><p><small>Only aggregate taste data is used; no personal data about individuals.</small></p>")
    css = ("body{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem;color:#1b1b1f}"
           "table{border-collapse:collapse;width:100%;font-size:.9rem}td,th{border:1px solid #ddd;padding:.35rem .5rem;text-align:left}"
           ".card{border:1px solid #ddd;border-radius:10px;padding:.8rem 1rem;margin:1rem 0}"
           ".pill{font-size:.75rem;background:#eef;border-radius:99px;padding:.1rem .6rem}"
           ".warn{background:#fff3cd;padding:.6rem;border-radius:8px}blockquote{margin:.5rem 0;color:#444}"
           "@media print{.card{break-inside:avoid}}")
    return f"<!doctype html><html><head><meta charset='utf-8'><title>Taste Lab report</title><style>{css}</style></head><body>{''.join(parts)}</body></html>"
