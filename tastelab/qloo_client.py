"""Qloo API client (hackathon API).

Live mode uses only documented GET endpoints with the ``X-Api-Key`` header:
  * GET /search      resolve a name to a Qloo entity id
  * GET /v2/insights taste-based recommendations from entity signals (+ optional location)

Demo mode (no key) reads synthetic fixtures from ``demo_data`` and flags every result with
``demo=True``. Every call, live or demo, is recorded in ``client.trace`` so the UI can show
exactly which Qloo signal produced each insight. The API key is never logged or serialized.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import requests

from . import config, demo_data


class QlooError(RuntimeError):
    """Raised for any failed Qloo call (message never contains the API key)."""


@dataclass
class Entity:
    id: str
    name: str
    type: str
    affinity: float | None = None
    demo: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "type": self.type,
                "affinity": self.affinity, "demo": self.demo}


def _urn(entity_type: str) -> str:
    return entity_type if entity_type.startswith("urn:") else f"urn:entity:{entity_type}"


def _short_type(urn_or_type: str) -> str:
    return urn_or_type.rsplit(":", 1)[-1]


@dataclass
class QlooClient:
    api_key: str | None = None
    base_url: str = config.DEFAULT_QLOO_BASE_URL
    demo: bool | None = None
    timeout: float = 20.0
    max_retries: int = 2
    session: Any = None
    trace: list[dict[str, Any]] = field(default_factory=list)
    _cache: dict[str, Any] = field(default_factory=dict)
    _last_ms: float = 0.0

    def __post_init__(self) -> None:
        if self.demo is None:
            self.demo = not bool(self.api_key)
        if self.session is None:
            self.session = requests.Session()
        self.base_url = self.base_url.rstrip("/")

    # ------------------------------------------------------------------ helpers
    @property
    def mode(self) -> str:
        return "demo" if self.demo else "live"

    def __repr__(self) -> str:  # never leak the key
        return f"QlooClient(mode={self.mode!r}, base_url={self.base_url!r})"

    def _record(self, endpoint: str, params: dict[str, Any], status: Any, ms: float, n: int) -> None:
        self.trace.append({"endpoint": endpoint, "params": dict(params), "status": status,
                           "latency_ms": round(ms), "results": n, "mode": self.mode})

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        if not self.api_key:
            raise QlooError("QLOO_API_KEY is not set; refusing to call the live API.")
        cache_key = path + "?" + "&".join(f"{k}={params[k]}" for k in sorted(params))
        if cache_key in self._cache:
            self._last_ms = 0.0
            return self._cache[cache_key]
        url = self.base_url + path
        headers = {"X-Api-Key": self.api_key, "Accept": "application/json"}
        last = "unknown error"
        for attempt in range(self.max_retries + 1):
            t0 = time.time()
            try:
                resp = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
            except requests.RequestException as exc:
                last = f"network error: {type(exc).__name__}"
                self._record(path, params, "network_error", (time.time() - t0) * 1000, 0)
                time.sleep(0.4 * (attempt + 1))
                continue
            ms = (time.time() - t0) * 1000
            if resp.status_code == 429 and attempt < self.max_retries:
                self._record(path, params, 429, ms, 0)
                time.sleep(1.0 * (attempt + 1))
                last = "rate limited (HTTP 429)"
                continue
            if resp.status_code >= 400:
                self._record(path, params, resp.status_code, ms, 0)
                raise QlooError(f"Qloo {path} returned HTTP {resp.status_code}")
            try:
                data = resp.json()
            except ValueError as exc:
                self._record(path, params, resp.status_code, ms, 0)
                raise QlooError(f"Qloo {path} returned non-JSON") from exc
            self._last_ms = ms
            self._cache[cache_key] = data
            return data
        raise QlooError(f"Qloo {path} failed: {last}")

    @staticmethod
    def _items(data: Any) -> list[dict[str, Any]]:
        results = data.get("results") if isinstance(data, dict) else data
        if isinstance(results, dict):
            results = results.get("entities") or results.get("results") or []
        return [r for r in (results or []) if isinstance(r, dict)]

    @staticmethod
    def _to_entity(raw: dict[str, Any], fallback_type: str, demo: bool) -> Entity | None:
        eid = raw.get("entity_id") or raw.get("id")
        name = raw.get("name")
        if not eid or not name:
            return None
        types = raw.get("types") or []
        etype = _short_type(types[0]) if types else _short_type(fallback_type)
        aff = None
        q = raw.get("query")
        if isinstance(q, dict) and isinstance(q.get("affinity"), (int, float)):
            aff = float(q["affinity"])
        return Entity(id=str(eid), name=str(name), type=etype, affinity=aff, demo=demo)

    # ------------------------------------------------------------------ public API
    def search(self, query: str, entity_type: str | None = None, take: int = 5) -> list[Entity]:
        """Resolve a free-text name to Qloo entities."""
        params: dict[str, Any] = {"query": query, "take": take}
        if entity_type:
            params["types"] = _urn(entity_type)
        if self.demo:
            raw = demo_data.demo_search(query, entity_type, take)
            self._record("/search", params, "demo", 0, len(raw))
            return [e for e in (self._to_entity(r, entity_type or "brand", True) for r in raw) if e]
        data = self._get("/search", params)
        items = self._items(data)
        self._record("/search", params, 200, self._last_ms, len(items))
        return [e for e in (self._to_entity(r, entity_type or "brand", False) for r in items) if e]

    def insights(self, entity_type: str, signal_ids: list[str], location: str | None = None,
                 take: int = 10) -> list[Entity]:
        """Taste-based recommendations of ``entity_type`` from entity signals (+ optional city)."""
        if not signal_ids:
            return []
        params: dict[str, Any] = {
            "filter.type": _urn(entity_type),
            "signal.interests.entities": ",".join(signal_ids),
            "take": take,
        }
        if location:
            params["filter.location.query"] = location
        if self.demo:
            raw = demo_data.demo_insights(_short_type(entity_type), signal_ids, location, take)
            self._record("/v2/insights", params, "demo", 0, len(raw))
            return [e for e in (self._to_entity(r, entity_type, True) for r in raw) if e]
        data = self._get("/v2/insights", params)
        items = self._items(data)
        self._record("/v2/insights", params, 200, self._last_ms, len(items))
        return [e for e in (self._to_entity(r, entity_type, False) for r in items) if e]


def client_from_env() -> QlooClient:
    key = None if config.force_demo() else config.qloo_api_key()
    return QlooClient(api_key=key, base_url=config.qloo_base_url(), demo=not bool(key))
