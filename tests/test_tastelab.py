import pytest

from tastelab import shopify
from tastelab.agents import Brief, run_taste_lab
from tastelab.llm import LLM, parse_json_loose
from tastelab.qloo_client import QlooClient, QlooError
from tastelab.report import to_csv, to_html, to_markdown


class FakeResp:
    def __init__(self, status=200, payload=None):
        self.status_code, self._p = status, payload if payload is not None else {}

    def json(self):
        return self._p


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params, headers))
        return self.responses.pop(0)


def brief():
    return Brief("Ridgeline Daypack", "Recycled nylon commuter daypack", "urban hikers", "USD 89",
                 "US + EU", ["Austin", "Berlin", "Amsterdam"], 3)


def test_demo_pipeline_end_to_end():
    client = QlooClient(api_key=None)
    assert client.mode == "demo"
    run = run_taste_lab(brief(), client, LLM(api_key=None))
    assert run["mode"] == "demo" and run["llm"] == "offline-fallback"
    assert len(run["personas"]) == 3
    assert [c["score"] for c in run["cities"]] == sorted((c["score"] for c in run["cities"]), reverse=True)
    for c in run["cities"]:
        assert set(c["by_persona"]) == {r["persona"]["name"] for r in run["personas"]}
        assert isinstance(c["vs_avg"], float)
    assert abs(sum(c["vs_avg"] for c in run["cities"])) < 0.5
    for r in run["personas"]:
        assert 1 <= r["reaction"]["score"] <= 10
        assert r["ad"]["headline"]
        for e in r["reaction"]["evidence"]:
            assert e in run["evidence"]
    assert run["trace"] and all(t["mode"] == "demo" for t in run["trace"])
    assert "DEMO MODE" in to_markdown(run) and "DEMO MODE" in to_html(run)


def test_live_requires_key_and_never_calls_network():
    c = QlooClient(api_key=None, demo=False, session=FakeSession([]))
    with pytest.raises(QlooError):
        c.search("Muji", "brand")
    assert c.session.calls == []


def test_live_request_shape_and_parsing():
    s = FakeSession([
        FakeResp(200, {"success": True, "results": [{"name": "Muji", "entity_id": "E1", "types": ["urn:entity:brand"]}]}),
        FakeResp(200, {"success": True, "results": {"entities": [
            {"name": "Aesop", "entity_id": "E2", "types": ["urn:entity:brand"], "query": {"affinity": 0.83}}]}}),
    ])
    c = QlooClient(api_key="SECRET", session=s)
    assert c.mode == "live"
    ent = c.search("Muji", "brand", take=1)[0]
    assert (ent.id, ent.name, ent.type, ent.demo) == ("E1", "Muji", "brand", False)
    out = c.insights("brand", ["E1"], location="Berlin", take=3)
    assert out[0].affinity == 0.83
    (u1, p1, h1), (u2, p2, h2) = s.calls
    assert u1.endswith("/search") and p1["types"] == "urn:entity:brand"
    assert u2.endswith("/v2/insights")
    assert p2["filter.type"] == "urn:entity:brand" and p2["signal.interests.entities"] == "E1"
    assert p2["filter.location.query"] == "Berlin"
    assert h1["X-Api-Key"] == "SECRET"
    assert "SECRET" not in repr(c) and "SECRET" not in str(c.trace)


def test_http_error_has_no_key_in_message_and_429_retries(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    s = FakeSession([FakeResp(429), FakeResp(200, {"results": []})])
    c = QlooClient(api_key="SECRET", session=s)
    assert c.search("x") == []
    s2 = FakeSession([FakeResp(401)])
    c2 = QlooClient(api_key="SECRET", session=s2)
    with pytest.raises(QlooError) as ei:
        c2.search("x")
    assert "401" in str(ei.value) and "SECRET" not in str(ei.value)


def test_json_loose_parser():
    assert parse_json_loose('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_loose('Sure! {"a": [1,2]} done') == {"a": [1, 2]}


def test_llm_failure_falls_back(monkeypatch):
    monkeypatch.setattr('time.sleep', lambda *_: None)
    class BadSession:
        def post(self, *a, **k):
            return FakeResp(500)
    llm = LLM(api_key="K", session=BadSession())
    assert llm.json("hi") is None and llm.warnings
    run = run_taste_lab(brief(), QlooClient(api_key=None), llm)
    assert run["personas"] and run["warnings"]


def test_ssrf_blocked():
    for bad in ["http://127.0.0.1/admin", "http://localhost:8000", "file:///etc/passwd", "http://10.0.0.5/"]:
        with pytest.raises(shopify.ProductPageError):
            shopify._check_url(bad)


def test_product_html_parsing():
    page = ('<script type="application/ld+json">{"@type":"Product","name":"Mug","description":"Nice mug",'
            '"offers":{"price":"19.00","priceCurrency":"USD"}}</script>')
    assert shopify.parse_product_html(page) == {"name": "Mug", "description": "Nice mug", "price": "USD 19.00"}
    og = '<meta property="og:title" content="Tea &amp; Co"><meta property="og:description" content="Loose leaf">'
    info = shopify.parse_product_html(og)
    assert info["name"] == "Tea & Co" and info["description"] == "Loose leaf"


def test_messy_llm_output_does_not_crash():
    class Messy(LLM):
        def __init__(self):
            super().__init__(api_key="k")

        def json(self, prompt, system=""):
            if "design buyer personas" in prompt:
                return {"personas": ["junk", {"name": "A", "seeds": ["Muji"]},
                                     {"name": "B", "tagline": "t", "seeds": [{"name": "Muji", "type": "Brand"}]},
                                     {"name": "C", "tagline": "t", "seeds": [{"name": "Bonobo", "type": "artist"}]}]}
            if "React in first" in prompt:
                return {"reaction": "ok", "score": "8", "loves": "one", "concerns": None, "evidence": "Q1"}
            if "moderate" in prompt:
                return {"synthesis": "x"}
            return {"headline": "h", "body": "b", "cta": "c", "hook_reason": "r", "evidence": "Q1"}

    run = run_taste_lab(brief(), QlooClient(api_key=None), Messy())
    assert [r["persona"]["name"] for r in run["personas"]] == ["B", "C"]
    assert run["personas"][0]["reaction"]["loves"] == ["one"] and run["personas"][0]["reaction"]["concerns"] == []


def test_csv_export_neutralises_formulas():
    run = run_taste_lab(brief(), QlooClient(api_key=None), LLM(api_key=None))
    run["personas"][0]["ad"]["headline"] = "=HYPERLINK(\"http://x\")"
    out = to_csv(run)
    assert out.splitlines()[0].startswith("persona,") and "'=HYPERLINK" in out


def test_radar_gap_playbook_and_whatif():
    from tastelab.agents import what_if

    b = brief()
    b.anchors = ["Patagonia", "Peak Design"]
    run = run_taste_lab(b, QlooClient(api_key=None), LLM(api_key=None))
    assert len(run["radar"]) == len(run["personas"])
    assert all(x.get("idea") for x in run["radar"])
    assert run["gap"] and run["gap"]["anchors"] and set(run["gap"]["match"]) == {r["persona"]["name"] for r in run["personas"]}
    assert len(run["playbook"]) == 4
    ids = set(run["evidence"])
    for x in run["radar"]:
        assert set(x["evidence"]) <= ids
    for s in run["playbook"]:
        assert set(s["evidence"]) <= ids
    rows = what_if(run, LLM(api_key=None), price="USD 49")
    assert len(rows) == len(run["personas"]) and all("delta" in r for r in rows)
    assert "Collaboration radar" in to_markdown(run) and "30 days" in to_html(run)


def test_no_anchors_means_no_gap():
    run = run_taste_lab(brief(), QlooClient(api_key=None), LLM(api_key=None))
    assert run["gap"] is None and run["radar"]


def test_ad_evidence_recovered_from_text():
    from tastelab.agents import ad_copy

    class Fake:
        available = True
        warnings: list = []
        def json(self, *a, **k):
            return {"headline": "H", "body": "Like Bon Iver [Q2].", "cta": "Go", "hook_reason": "Uses Q2", "evidence": []}

    sig = {"signature": {"artist": [{"name": "Bon Iver", "affinity": .9, "evidence": "Q2"}]}}
    out = ad_copy(brief(), {"name": "P", "tagline": ""}, sig, {"concerns": []}, Fake())
    assert out["evidence"] == ["Q2"] and "[Q2]" not in out["body"]


def test_markdown_table_survives_pipe_in_name():
    run = run_taste_lab(brief(), QlooClient(api_key=None), LLM(api_key=None))
    first = next(iter(run["evidence"].values()))
    first["entity"] = "TDQ Steaks | Toro Dorado"
    md = to_markdown(run)
    assert "TDQ Steaks / Toro Dorado" in md


def test_thin_seed_list_is_topped_up():
    from tastelab.agents import Evidence, build_signature

    persona = {"name": "X", "tagline": "", "seeds": [("IKEA", "brand")]}
    sig = build_signature(QlooClient(api_key=None), Evidence(), persona)
    assert len(sig["seed_ids"]) >= 3


def test_radar_keeps_only_partners_the_model_picks():
    from tastelab.agents import radar_idea

    cand = {"brand": [{"name": "Porsche", "affinity": .9, "evidence": "Q1"}, {"name": "Osprey", "affinity": .9, "evidence": "Q2"}],
            "artist": [{"name": "Tycho", "affinity": .9, "evidence": "Q3"}], "venue": []}
    row = {"persona": "P", "city": "Berlin", "cand": cand}

    class Fake:
        available = True
        warnings: list = []
        def json(self, *a, **k):
            return {"idea": "Pop-up with Osprey.", "evidence": ["Q2"]}

    out = radar_idea(brief(), row, Fake())
    assert out["brand"]["name"] == "Osprey" and out["artist"] is None and out["evidence"] == ["Q2"]
