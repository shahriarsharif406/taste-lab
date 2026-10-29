"""Visual layer for the Streamlit app: a swatch-card ("colour chip") system.

Every persona is a colour chip. Its colour follows it through the personas, cities and ad tabs.
All dynamic text is HTML-escaped (LLM output and product pages are untrusted).
"""

from __future__ import annotations

import html
from typing import Any

PALETTE = ["#7B1E3A", "#2F5D50", "#2748C6", "#E7B7C8", "#C99A2E"]  # claret, bottle green, cobalt, blush, ochre

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,400..800;1,6..96,400..700&family=Instrument+Sans:ital,wght@0,400..700;1,400..600&display=swap');
:root{--ink:#1A1A1A;--paper:#F5F5F3;--wash:#ECECE8;--mute:#66665F;--line:#D6D5CF;--serif:'Bodoni Moda','Didot',Georgia,serif;}
html,body,.stApp,[class*="css"]{font-family:'Instrument Sans',system-ui,sans-serif;color:var(--ink)}
.stApp{background:var(--paper)}
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{visibility:hidden;height:0}
[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:1.6rem;max-width:1240px}
h1,h2,h3,h4{font-family:var(--serif)!important;font-weight:600;letter-spacing:-.01em;color:var(--ink)}
[data-testid="stSidebar"]{background:var(--wash);border-right:1px solid var(--line)}
[data-testid="stSidebar"] h2{font-size:1.6rem;margin-bottom:.4rem}
[data-testid="stSidebar"] label p{font-weight:600;font-size:.9rem}
[data-testid="stSidebar"] input,[data-testid="stSidebar"] textarea,[data-testid="stSidebar"] [data-baseweb="select"]>div{background:#fff!important;border-radius:0!important;border:1px solid var(--line)!important}
.stButton>button,.stDownloadButton>button{border-radius:0;border:1.5px solid var(--ink);font-weight:600;background:transparent;color:var(--ink)}
.stButton>button:hover,.stDownloadButton>button:hover{background:var(--ink);color:#fff;border-color:var(--ink)}
button[data-testid="stBaseButton-primary"],.stButton>button[kind="primary"]{background:var(--ink);color:#fff;padding:.7rem 1rem;font-size:1.02rem}
button[data-testid="stBaseButton-primary"]:hover{background:#000}
.stTabs [data-baseweb="tab-list"]{gap:1.8rem;border-bottom:1px solid var(--ink)}
.stTabs [data-baseweb="tab"]{padding:.7rem 0;font-weight:600;color:var(--mute)}
.stTabs [aria-selected="true"]{color:var(--ink)}
.stTabs [data-baseweb="tab-highlight"]{background:var(--ink);height:3px}
.stTabs [data-baseweb="tab-border"]{display:none}
:focus-visible{outline:3px solid #2748C6!important;outline-offset:2px}

.tl-hero{display:grid;grid-template-columns:1.5fr 1fr;gap:2.5rem;align-items:end;padding:.6rem 0 1.8rem;border-bottom:2px solid var(--ink);margin-bottom:1.4rem}
.tl-title{font-family:var(--serif);font-size:clamp(3.4rem,8.5vw,7.4rem);line-height:.9;letter-spacing:-.035em;font-weight:500;margin:0}
.tl-sub{font-size:1.25rem;max-width:30ch;line-height:1.4;margin:1.8rem 0 0}
.tl-strip{display:flex;align-items:flex-end;gap:7px;height:170px}
.tl-strip div{flex:1}
.tl-strip-cap{font-size:.85rem;color:var(--mute);margin-top:.6rem}

.tl-note{background:var(--wash);border-left:3px solid var(--ink);padding:.65rem .95rem;font-size:.93rem;margin:.5rem 0;line-height:1.45}
.tl-note.warn{border-left-color:#C99A2E;background:#F3EBD6}
.tl-note.live{border-left-color:#2F5D50;background:#E1EBE6}

.tl-verdict h3{font-size:1.1rem;margin:1.2rem 0 .3rem}
.tl-verdict p{font-family:var(--serif);font-size:1.55rem;line-height:1.45;max-width:62ch;margin:0 0 1.2rem}

.tl-plate{background:#fff;border:1px solid var(--line);height:100%;margin-bottom:1.2rem}
.tl-plate-top{padding:1.3rem 1.4rem 1.2rem;min-height:215px;display:flex;flex-direction:column;justify-content:space-between}
.tl-score{font-family:var(--serif);font-size:5.6rem;line-height:.88;font-weight:500;letter-spacing:-.04em}
.tl-score small{font-size:1.3rem;font-weight:400;opacity:.75;margin-left:.25rem;letter-spacing:0}
.tl-pname{font-family:var(--serif);font-size:1.75rem;line-height:1.08;font-weight:600;margin-top:1.1rem}
.tl-tag{font-size:.95rem;font-style:italic;margin-top:.3rem;opacity:.92}
.tl-plate-body{padding:1.2rem 1.4rem 1.4rem}
.tl-quote{font-family:var(--serif);font-size:1.12rem;line-height:1.55;margin:0 0 1.1rem}
.tl-cols{display:grid;grid-template-columns:1fr 1fr;gap:1.1rem;font-size:.92rem;line-height:1.45}
.tl-cols h4{font-family:'Instrument Sans',sans-serif!important;font-size:.95rem;margin:0 0 .3rem;font-weight:700}
.tl-cols ul{margin:0;padding-left:1.05rem}
.tl-sig{margin-top:1.1rem;border-top:1px solid var(--line);padding-top:.5rem}
.tl-sig-label{font-size:.85rem;color:var(--mute);margin:.7rem 0 .3rem}
.tl-chips{display:flex;flex-wrap:wrap;gap:.35rem}
.tl-chip{font-size:.83rem;border:1px solid var(--line);border-radius:99px;padding:.14rem .62rem;background:#fff;white-space:nowrap}
.tl-chip i{font-style:normal;color:var(--mute);font-size:.72rem;margin-left:.35rem}

.tl-city{display:grid;grid-template-columns:190px 1fr 110px;gap:.2rem 1.2rem;align-items:center;padding:1rem 0;border-bottom:1px solid var(--line)}
.tl-city-name{font-family:var(--serif);font-size:1.75rem;font-weight:500}
.tl-track{position:relative;height:16px;background:var(--wash)}
.tl-track:after{content:"";position:absolute;left:50%;top:-5px;bottom:-5px;width:1px;background:var(--ink)}
.tl-bar{position:absolute;top:0;bottom:0}
.tl-city-score{text-align:right;font-weight:600}
.tl-city-score small{display:block;font-weight:400;color:var(--mute);font-size:.8rem}
.tl-places{grid-column:2 / 4;font-size:.88rem;color:var(--mute);line-height:1.5}
.tl-best{display:flex;flex-wrap:wrap;gap:.6rem;margin:.6rem 0 1.4rem}
.tl-best span{padding:.45rem .85rem;font-weight:600;font-size:.92rem}
.tl-best b{font-family:var(--serif);font-size:1.1rem;font-weight:600;margin-left:.4rem}

.tl-ad{padding:1.6rem 1.6rem 1.4rem;min-height:300px;display:flex;flex-direction:column;justify-content:space-between;margin-bottom:1.2rem}
.tl-ad-for{font-size:.9rem;opacity:.9}
.tl-ad h3{font-family:var(--serif)!important;font-size:2.35rem;line-height:1.04;margin:.5rem 0 .9rem;font-weight:600;color:inherit}
.tl-ad p{font-size:1.02rem;max-width:38ch;line-height:1.5;margin:0 0 1.1rem}
.tl-ad-cta{display:inline-block;border:1.5px solid currentColor;padding:.45rem 1.1rem;font-weight:600;width:max-content}
.tl-ad-why{font-size:.82rem;opacity:.88;margin-top:1.1rem;line-height:1.4}

@media (max-width:820px){.tl-hero{grid-template-columns:1fr}.tl-strip{height:110px}.tl-city{grid-template-columns:1fr 90px}.tl-track{grid-column:1 / 3}.tl-places{grid-column:1 / 3}.tl-cols{grid-template-columns:1fr}}
@media (prefers-reduced-motion:no-preference){.tl-strip div{animation:tl-rise .9s cubic-bezier(.2,.7,.2,1) both}.tl-strip div:nth-child(2){animation-delay:.07s}.tl-strip div:nth-child(3){animation-delay:.14s}.tl-strip div:nth-child(4){animation-delay:.21s}.tl-strip div:nth-child(5){animation-delay:.28s}}
@keyframes tl-rise{from{transform:scaleY(.15);transform-origin:bottom}to{transform:scaleY(1);transform-origin:bottom}}
"""

e = html.escape


def text_on(bg: str) -> str:
    """Readable text colour (ink or white) for a hex background."""
    h = bg.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = [(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4) for c in (r, g, b)]
    lum = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    return "#1A1A1A" if lum > 0.32 else "#FFFFFF"


def persona_colors(names: list[str]) -> dict[str, str]:
    return {n: PALETTE[i % len(PALETTE)] for i, n in enumerate(names)}


def style_tag() -> str:
    return f"<style>{CSS}</style>"


def hero() -> str:
    heights = [100, 84, 93, 76, 88]
    strip = "".join(f'<div style="background:{c};height:{h}%"></div>' for c, h in zip(PALETTE, heights))
    return (
        '<div class="tl-hero"><div>'
        '<div class="tl-title">Taste Lab</div>'
        '<p class="tl-sub">Know who will love your product, in which city, and what to say to them.</p>'
        f'</div><div><div class="tl-strip">{strip}</div>'
        '<div class="tl-strip-cap">Every buyer persona is built from Qloo taste data.</div></div></div>'
    )


def note(text: str, kind: str = "") -> str:
    return f'<div class="tl-note {kind}">{text}</div>'


def verdict(text: str) -> str:
    return f'<div class="tl-verdict"><h3>What the focus group says</h3><p>{e(text)}</p></div>'


def _chips(rows: list[dict[str, Any]]) -> str:
    return "".join(f'<span class="tl-chip">{e(r["name"])}<i>{e(r["evidence"])}</i></span>' for r in rows)


def plate(r: dict[str, Any], color: str) -> str:
    p, rx, sig = r["persona"], r["reaction"], r["signature"]["signature"]
    fg = text_on(color)
    loves = "".join(f"<li>{e(x)}</li>" for x in rx["loves"])
    concerns = "".join(f"<li>{e(x)}</li>" for x in rx["concerns"])
    labels = {"artist": "Music they follow", "brand": "Brands they buy", "movie": "Films they watch"}
    sigs = "".join(f'<div class="tl-sig-label">{labels.get(t, t)}</div><div class="tl-chips">{_chips(rows)}</div>'
                   for t, rows in sig.items() if rows)
    return (
        '<div class="tl-plate">'
        f'<div class="tl-plate-top" style="background:{color};color:{fg}">'
        f'<div class="tl-score">{int(rx["score"])}<small>of 10 intent to buy</small></div>'
        f'<div><div class="tl-pname">{e(p["name"])}</div><div class="tl-tag">{e(p["tagline"])}</div></div></div>'
        '<div class="tl-plate-body">'
        f'<p class="tl-quote">{e(rx["reaction"])}</p>'
        f'<div class="tl-cols"><div><h4>Likes</h4><ul>{loves}</ul></div><div><h4>Hesitations</h4><ul>{concerns}</ul></div></div>'
        f'<div class="tl-sig">{sigs}</div></div></div>'
    )


def cities(rows: list[dict[str, Any]], colors: dict[str, str]) -> str:
    maxabs = max((abs(c.get("vs_avg", 0)) for c in rows), default=0) or 1
    out = []
    for c in rows:
        v = c.get("vs_avg", 0)
        width = abs(v) / maxabs * 50
        left = 50 if v >= 0 else 50 - width
        color = "#1A1A1A" if v >= 0 else "#B3B2AB"
        places = ", ".join(f'{e(p["name"])} <span class="tl-chip" style="padding:0 .4rem">{e(p["evidence"])}</span>'
                           for p in c["top_places"]) or "No places returned"
        out.append(
            '<div class="tl-city">'
            f'<div class="tl-city-name">{e(c["city"])}</div>'
            f'<div class="tl-track"><div class="tl-bar" style="left:{left:.1f}%;width:{width:.1f}%;background:{color}"></div></div>'
            f'<div class="tl-city-score">{c["score"]:.1f}<small>{v:+.1f} vs average</small></div>'
            f'<div class="tl-places">{places}</div></div>')
    return "".join(out)


def best_city(rows: list[dict[str, Any]], colors: dict[str, str]) -> str:
    best: dict[str, tuple[str, float]] = {}
    for c in rows:
        for n, v in c.get("by_persona", {}).items():
            if n not in best or v > best[n][1]:
                best[n] = (c["city"], v)
    chips = "".join(
        f'<span style="background:{colors.get(n, "#1A1A1A")};color:{text_on(colors.get(n, "#1A1A1A"))}">'
        f'{e(n)}<b>{e(c)}</b></span>' for n, (c, _) in best.items())
    return f'<div class="tl-best">{chips}</div>' if chips else ""


def ad(r: dict[str, Any], color: str) -> str:
    a, fg = r["ad"], text_on(color)
    ev = ", ".join(e(x) for x in a["evidence"]) or "none"
    return (
        f'<div class="tl-ad" style="background:{color};color:{fg}"><div>'
        f'<div class="tl-ad-for">For {e(r["persona"]["name"])}</div>'
        f'<h3>{e(a["headline"])}</h3><p>{e(a["body"])}</p>'
        f'<span class="tl-ad-cta">{e(a["cta"])}</span></div>'
        f'<div class="tl-ad-why">Why this hook: {e(a["hook_reason"])} Evidence {ev}.</div></div>'
    )
