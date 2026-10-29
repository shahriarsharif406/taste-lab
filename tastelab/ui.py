"""Visual layer for the Streamlit app: a swatch-card ("colour chip") system.

Every persona is a colour chip. Its colour follows it through the personas, cities and ad tabs.
All dynamic text is HTML-escaped (LLM output and product pages are untrusted).
"""

from __future__ import annotations

import html
from typing import Any

PALETTE = ["#5E1B2E", "#24413A", "#1D2B4F", "#D6B4AC", "#A98749"]  # oxblood, deep pine, midnight navy, rose quartz, antique brass

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

[data-testid="stSidebar"] [data-baseweb="base-input"],[data-testid="stSidebar"] [data-baseweb="input"],[data-testid="stSidebar"] [data-baseweb="input"]>div,[data-testid="stSidebar"] [data-baseweb="textarea"],[data-testid="stSidebar"] [data-baseweb="textarea"]>div,[data-testid="stSidebar"] [data-baseweb="select"]>div,[data-testid="stSidebar"] [data-baseweb="select"] div{background:transparent!important;background-color:transparent!important}
[data-testid="stSidebar"] [data-baseweb="select"] div,[data-testid="stSidebar"] [data-baseweb="select"] span{color:#fff!important}
[data-testid="stSidebar"] [data-testid="stTextInput"] div,[data-testid="stSidebar"] [data-testid="stTextArea"] div,[data-testid="stSidebar"] [data-testid="stSelectbox"] div{background:transparent!important;background-color:transparent!important;border-radius:0!important}
[data-testid="stSidebar"] [data-testid="stSelectbox"] div{color:#fff!important}
.stTabs [data-baseweb="tab"] p{font-family:var(--serif)!important;font-style:italic;font-size:1.5rem!important;font-weight:500}
[data-testid="stSidebar"] input::placeholder{color:#8d8d86!important;opacity:1}
/* ---- v2: runway cover, black wardrobe sidebar, ticker ---- */
.block-container{padding-top:1rem;max-width:1320px}
[data-testid="stSidebar"]{background:#141414;border-right:0}
[data-testid="stSidebar"] *{color:#F3F3F1}
[data-testid="stSidebar"] h2{font-family:var(--serif)!important;font-style:italic;font-size:2rem;font-weight:500;color:#fff}
[data-testid="stSidebar"] label p{font-weight:500;font-size:.88rem;color:#BDBDB6}
[data-testid="stSidebar"] input,[data-testid="stSidebar"] textarea{background:transparent!important;color:#fff!important;border:0!important;border-bottom:1px solid #6b6b66!important;border-radius:0!important;padding-left:0!important}
[data-testid="stSidebar"] [data-baseweb="select"]>div{background:transparent!important;border:0!important;border-bottom:1px solid #6b6b66!important;border-radius:0!important}
[data-testid="stSidebar"] [data-baseweb="input"],[data-testid="stSidebar"] [data-baseweb="textarea"]{background:transparent!important;border:0!important}
[data-testid="stSidebar"] .stButton>button{border:1px solid #F3F3F1;color:#F3F3F1;background:transparent}
[data-testid="stSidebar"] .stButton>button:hover{background:#F3F3F1;color:#141414}
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]{background:#F3F3F1;color:#141414;font-size:1.05rem;padding:.8rem 1rem}
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] *{color:#141414}
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover{background:#E7B7C8}

.tl-cover{position:relative;display:flex;height:clamp(250px,31vw,400px);overflow:hidden}
.tl-cover .band{height:100%;transform-origin:bottom}
.tl-mast{position:absolute;left:2.2%;bottom:-.06em;font-family:var(--serif);font-style:italic;font-weight:500;font-size:clamp(4.4rem,15vw,13rem);line-height:.9;letter-spacing:-.045em;color:#fff;mix-blend-mode:difference;pointer-events:none;white-space:nowrap}
.tl-subline{display:flex;justify-content:space-between;align-items:baseline;gap:2rem;flex-wrap:wrap;padding:1rem 0 1.4rem;border-bottom:2px solid var(--ink);margin-bottom:1.2rem}
.tl-subline p{margin:0;font-family:var(--serif);font-style:italic;font-size:clamp(1.3rem,2.4vw,2rem);line-height:1.2;max-width:30ch}
.tl-subline small{font-size:.9rem;color:var(--mute);max-width:34ch}

.tl-ticker{background:#141414;color:#F3F3F1;overflow:hidden;white-space:nowrap;margin:.2rem 0 1.4rem;padding:.8rem 0}
.tl-ticker-in{display:inline-block;animation:tl-slide 70s linear infinite}
.tl-ticker:hover .tl-ticker-in{animation-play-state:paused}
.tl-ticker span{font-family:var(--serif);font-style:italic;font-size:1.5rem;margin:0 .9rem}
.tl-ticker i{display:inline-block;width:.55rem;height:.55rem;margin:0 .6rem .12rem}
@keyframes tl-slide{from{transform:translateX(0)}to{transform:translateX(-50%)}}

.tl-verdict{position:relative;padding-left:5.5rem;margin:1rem 0 1.8rem}
.tl-verdict:before{content:"\\201C";position:absolute;left:0;top:-.6rem;font-family:var(--serif);font-size:9rem;line-height:1;color:#7B1E3A}
.tl-verdict p{font-style:italic;font-size:clamp(1.4rem,2.2vw,1.95rem);max-width:56ch}
.tl-verdict h3{font-family:'Instrument Sans',sans-serif!important;font-size:.95rem;color:var(--mute);font-weight:600;margin:0 0 .4rem}

.stTabs [data-baseweb="tab"]{font-family:var(--serif);font-style:italic;font-size:1.45rem;font-weight:500;padding:.6rem 0 .8rem}
.stTabs [data-baseweb="tab-list"]{gap:2.4rem;margin-bottom:.6rem}

.tl-plate{border:0;background:#fff;box-shadow:0 0 0 1px var(--line)}
.tl-plate-top{position:relative;min-height:300px;padding:1.6rem 1.7rem}
.tl-plate-top:after,.tl-ad:after{content:"";position:absolute;inset:12px;border:1px solid currentColor;opacity:.38;pointer-events:none}
.tl-score{font-size:clamp(6.5rem,10vw,9rem);font-weight:400}
.tl-score small{font-size:1.2rem;font-style:italic}
.tl-pname{font-size:2.2rem;line-height:1.02;font-style:italic;font-weight:500}
.tl-tag{font-size:1rem;font-style:normal}

.tl-city{grid-template-columns:minmax(220px,300px) 1fr 120px;padding:1.3rem 0}
.tl-city-name{font-size:clamp(2.2rem,4vw,3.6rem);font-style:italic;line-height:1}
.tl-track{height:22px}
.tl-city-score{font-family:var(--serif);font-size:2rem;font-weight:500}
.tl-best span{padding:.7rem 1.1rem;font-size:.95rem}
.tl-best b{font-size:1.5rem;font-style:italic;font-weight:500;margin-left:.6rem}
.tl-ad{position:relative;min-height:380px;padding:2rem 2rem 1.7rem}
.tl-ad h3{font-size:clamp(2.4rem,4vw,3.3rem);font-style:italic;font-weight:500;line-height:1}
.tl-ad p{font-size:1.08rem}
@media (max-width:820px){.tl-city{grid-template-columns:1fr 90px}.tl-verdict{padding-left:0}.tl-verdict:before{display:none}.tl-cover{height:220px}}
@media (prefers-reduced-motion:no-preference){.tl-cover .band{animation:tl-rise 1s cubic-bezier(.2,.7,.2,1) both}.tl-cover .band:nth-child(2){animation-delay:.08s}.tl-cover .band:nth-child(3){animation-delay:.16s}.tl-cover .band:nth-child(4){animation-delay:.24s}.tl-cover .band:nth-child(5){animation-delay:.32s}}
@media (prefers-reduced-motion:reduce){.tl-ticker-in{animation:none}}

button[role="tab"],button[role="tab"] *{font-family:var(--serif)!important;font-style:italic!important;font-size:1.55rem!important;font-weight:500!important}
/* ---- v3: fabric, grain, restraint ---- */
:root{--paper:#F7F7F6;--wash:#EFEFED;--line:#DAD9D5;--grain:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 .5  0 0 0 0 .5  0 0 0 0 .5  0 0 0 .55 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>")}
.stApp{background:var(--paper)}
.block-container{padding-top:.6rem}
.tl-cover{gap:3px;background:var(--paper)}
.tl-cover .band{position:relative;background-image:linear-gradient(172deg,rgba(255,255,255,.16) 0%,rgba(255,255,255,0) 38%,rgba(0,0,0,.28) 100%)}
.tl-cover .band:after,.tl-plate-top:before,.tl-ad:before{content:"";position:absolute;inset:0;background-image:var(--grain);mix-blend-mode:overlay;opacity:.55;pointer-events:none}
.tl-mast{mix-blend-mode:normal;color:#fff;font-weight:400;letter-spacing:-.05em;font-size:clamp(4rem,13.5vw,12rem);left:2.4%;bottom:-.04em;text-shadow:0 2px 40px rgba(0,0,0,.25)}
.tl-subline{border-bottom:1px solid var(--ink);padding:1.2rem 0 1.5rem}
.tl-subline p{font-weight:400}
.tl-plate{box-shadow:0 1px 0 var(--line),0 18px 40px -28px rgba(0,0,0,.35)}
.tl-plate-top{background-image:linear-gradient(165deg,rgba(255,255,255,.14),rgba(0,0,0,.26))}
.tl-score{font-weight:300;letter-spacing:-.05em}
.tl-ad{background-image:linear-gradient(165deg,rgba(255,255,255,.12),rgba(0,0,0,.24))}
.tl-ad:after,.tl-plate-top:after{opacity:.3}
.tl-ad-cta{border-width:1px;padding:.55rem 1.4rem;font-weight:500}
.tl-chip{border-color:var(--line);background:transparent}
.tl-track{height:6px;background:var(--line)}
.tl-track:after{top:-9px;bottom:-9px}
.tl-city{padding:1.5rem 0;border-bottom:1px solid var(--line)}
.tl-city-name{font-weight:400}
.tl-best span{border-radius:0;box-shadow:0 12px 24px -18px rgba(0,0,0,.45)}
.tl-ticker{background:#0E0E0E;padding:1rem 0}
.tl-ticker span{font-size:1.35rem;opacity:.92}
.tl-note{background:transparent;border:0;border-left:2px solid var(--ink);padding:.3rem .9rem;color:#4a4a45}
.tl-note.warn{border-left-color:#A98749;background:transparent}
.tl-note.live{border-left-color:#24413A;background:transparent}
.tl-verdict:before{color:#5E1B2E;font-weight:400}
.tl-foot{margin:3rem 0 1rem;padding-top:1rem;border-top:1px solid var(--ink);font-family:var(--serif);font-style:italic;font-size:1.15rem;color:#4a4a45}
[data-testid="stSidebar"]{background:#0E0E0E}
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover{background:#D6B4AC}
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
    flex = [3, 2, 4, 1.4, 2.4]
    bands = "".join(f'<div class="band" style="flex:{f};background:{c}"></div>' for c, f in zip(PALETTE, flex))
    return (f'<div class="tl-cover">{bands}<div class="tl-mast">Taste Lab</div></div>'
            '<div class="tl-subline"><p>Know who will love it, where they live, and what to say to them.</p>'
            '<small>Buyer personas built from Qloo taste data, tested by a synthetic focus group.</small></div>')


def ticker(names: list[str]) -> str:
    uniq = list(dict.fromkeys(n for n in names if n))[:28]
    if len(uniq) < 4:
        return ""
    one = "".join(f'<span>{e(n)}</span><i style="background:{PALETTE[k % len(PALETTE)]}"></i>' for k, n in enumerate(uniq))
    return f'<div class="tl-ticker" aria-label="Qloo taste signals found in this run"><div class="tl-ticker-in">{one}{one}</div></div>'


def footer() -> str:
    return '<div class="tl-foot">Taste signals from Qloo. Copy and reactions written with Gemini. No personal data about individuals is used.</div>'


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
