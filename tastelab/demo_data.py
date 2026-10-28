"""SYNTHETIC fixtures used only in demo mode (no Qloo key).

Nothing here is Qloo data. Demo results are always flagged ``demo=True`` and the UI
shows a banner so they can never be mistaken for live Qloo output.
"""

from __future__ import annotations

import hashlib

POOL: dict[str, list[str]] = {
    "artist": [
        "Khruangbin", "Phoebe Bridgers", "Tame Impala", "Fleet Foxes", "Bonobo",
        "Tyler, the Creator", "Mitski", "Four Tet", "Japanese Breakfast", "Kendrick Lamar",
        "Caribou", "Beach House", "FKA twigs", "Jungle", "Men I Trust", "Rosalia",
    ],
    "brand": [
        "Patagonia", "Aesop", "Allbirds", "Everlane", "Blue Bottle Coffee", "Muji",
        "Arc'teryx", "Le Labo", "Oatly", "Rapha", "Kinfolk", "Aritzia", "Glossier",
    ],
    "movie": [
        "Lost in Translation", "Moonrise Kingdom", "The Grand Budapest Hotel", "Past Lives",
        "Everything Everywhere All at Once", "Her", "Aftersun", "Portrait of a Lady on Fire",
    ],
    "place": [
        "Third-wave coffee roastery", "Vinyl record cafe", "Independent bookstore", "Natural wine bar",
        "Rooftop cinema", "Ceramics studio", "Plant-based bistro", "Indie live-music venue",
        "Weekend design market", "Specialty tea house", "Climbing gym", "Art-house cinema",
    ],
}

# Typical seed entities per archetype keyword (used by the offline persona planner)
ARCHETYPES: list[dict] = [
    {
        "name": "The Slow-Living Minimalist",
        "tagline": "Buys less, buys better; values craft and calm",
        "seeds": [("Muji", "brand"), ("Bonobo", "artist"), ("Lost in Translation", "movie")],
    },
    {
        "name": "The Indie Culture Explorer",
        "tagline": "Discovers things before they trend; lives at gigs and bookshops",
        "seeds": [("Phoebe Bridgers", "artist"), ("Kinfolk", "brand"), ("Past Lives", "movie")],
    },
    {
        "name": "The Outdoor Urbanite",
        "tagline": "City job, weekend trails; performance meets style",
        "seeds": [("Patagonia", "brand"), ("Khruangbin", "artist"), ("Moonrise Kingdom", "movie")],
    },
    {
        "name": "The Conscious Early Adopter",
        "tagline": "Tries new products if the values and design check out",
        "seeds": [("Allbirds", "brand"), ("Four Tet", "artist"), ("Her", "movie")],
    },
]

CITY_BIAS = {
    # purely synthetic variance so the demo chart is not flat
    "austin": 0.07, "berlin": 0.09, "amsterdam": 0.05, "portland": 0.08, "london": 0.04,
    "brooklyn": 0.06, "paris": 0.03, "lisbon": 0.05, "seattle": 0.04,
}


def stable_int(*parts: str) -> int:
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(h[:12], 16)


def entity_id(name: str, etype: str) -> str:
    return "DEMO-" + hashlib.sha1(f"{etype}:{name}".encode()).hexdigest()[:10].upper()


def demo_search(query: str, etype: str | None, take: int) -> list[dict]:
    q = query.strip().lower()
    types = [etype] if etype in POOL else list(POOL)
    hits: list[dict] = []
    for t in types:
        for name in POOL[t]:
            if q and (q in name.lower() or name.lower() in q):
                hits.append({"name": name, "entity_id": entity_id(name, t), "types": [f"urn:entity:{t}"]})
    if not hits:
        t = etype if etype in POOL else "brand"
        hits.append({"name": query.strip().title() or "Unknown", "entity_id": entity_id(query, t),
                     "types": [f"urn:entity:{t}"]})
    return hits[:take]


def demo_insights(etype: str, signals: list[str], location: str | None, take: int) -> list[dict]:
    t = etype if etype in POOL else "brand"
    seed = "|".join(sorted(signals)) + "|" + (location or "")
    pool = POOL[t]
    ranked = sorted(pool, key=lambda n: stable_int(seed, n))
    bias = CITY_BIAS.get((location or "").strip().lower(), 0.0)
    out = []
    for i, name in enumerate(ranked[:take]):
        base = 0.93 - i * 0.045 + (stable_int(seed, name, "j") % 40) / 1000.0
        aff = max(0.3, min(0.99, base - 0.1 + bias))
        label = name if t != "place" or not location else f"{name} ({location})"
        out.append({
            "name": label,
            "entity_id": entity_id(label, t),
            "types": [f"urn:entity:{t}"],
            "query": {"affinity": round(aff, 3)},
        })
    return out
