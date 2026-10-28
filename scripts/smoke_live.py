"""Run this the moment your Qloo key arrives to verify the live integration.

    QLOO_API_KEY=... python scripts/smoke_live.py

It makes 2 real calls (search + insights), prints what came back, and exits non-zero on failure.
If the printed shape differs from what tastelab/qloo_client.py expects, adjust _items/_to_entity there.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tastelab import config  # noqa: E402
from tastelab.qloo_client import QlooClient, QlooError  # noqa: E402

config.load_dotenv()
key = config.qloo_api_key()
if not key:
    sys.exit("QLOO_API_KEY is not set")

c = QlooClient(api_key=key, base_url=config.qloo_base_url(), demo=False)
try:
    hits = c.search("Patagonia", "brand", take=3)
    print("search ->", [(h.name, h.id) for h in hits])
    assert hits, "search returned nothing; check the response shape"
    recs = c.insights("brand", [hits[0].id], take=5)
    print("insights(brand) ->", [(r.name, r.affinity) for r in recs])
    places = c.insights("place", [hits[0].id], location="Berlin", take=5)
    print("insights(place, Berlin) ->", [(p.name, p.affinity) for p in places])
except QlooError as exc:
    sys.exit(f"FAILED: {exc}")
print("trace:", c.trace)
print("OK")
