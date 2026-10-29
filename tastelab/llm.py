"""Thin Gemini REST wrapper. If no key is set (or a call fails) callers use deterministic
offline fallbacks, so the pipeline always completes. The key is sent only as a header."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from . import config


_GOOD_MODEL: dict[str, str] = {}  # remembers the model that last worked, across runs


@dataclass
class LLM:
    api_key: str | None = None
    model: str = config.DEFAULT_GEMINI_MODEL
    timeout: float = 45.0
    session: Any = None
    warnings: list[str] = field(default_factory=list)
    fast_thinking: bool = True

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def __repr__(self) -> str:
        return f"LLM(model={self.model!r}, available={self.available})"

    def candidates(self) -> list[str]:
        """Flash models this key can use, newest first (plain Flash before Lite)."""
        if getattr(self, "_cands", None) is not None:
            return self._cands
        names: list[str] = []
        try:
            r = self.session.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                                 headers={"x-goog-api-key": self.api_key}, timeout=20)
            if r.status_code < 400:
                for m in r.json().get("models", []):
                    n = m.get("name", "").removeprefix("models/")
                    if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in n \
                            and not any(x in n for x in ("image", "tts", "live", "audio", "robotics", "embed")):
                        names.append(n)
        except Exception:  # noqa: BLE001 - discovery is best-effort
            pass

        def key(n: str):
            nums = re.findall(r"\d+(?:\.\d+)?", n)
            return ("lite" not in n, "preview" not in n and "exp" not in n, float(nums[0]) if nums else 0, n)
        self._cands = sorted(set(names), key=key, reverse=True)
        return self._cands

    def _call(self, model: str, prompt: str, system: str, thinking: bool):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        cfg: dict[str, Any] = {"temperature": 0.7, "responseMimeType": "application/json"}
        if thinking:
            cfg["thinkingConfig"] = {"thinkingLevel": "low"}
        body: dict[str, Any] = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": cfg}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        return self.session.post(url, json=body, timeout=self.timeout, headers={"x-goog-api-key": self.api_key})

    def json(self, prompt: str, system: str = "") -> Any | None:
        """Ask for a JSON answer. Returns parsed JSON or None (caller falls back).

        Retries busy (429/503) and timed-out calls, then moves on to the next available Flash model."""
        if not self.available:
            return None
        self.model = _GOOD_MODEL.get("m", self.model)
        order = [self.model] + [m for m in self.candidates() if m != self.model]
        last = "no model available"
        for model in order[:4]:
            thinking = self.fast_thinking
            for attempt in range(3):
                try:
                    resp = self._call(model, prompt, system, thinking)
                    if resp.status_code == 400 and thinking:
                        thinking = False  # model rejects thinkingConfig
                        resp = self._call(model, prompt, system, False)
                    if resp.status_code in (429, 500, 502, 503, 504):
                        last = f"{model} busy (HTTP {resp.status_code})"
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    if resp.status_code >= 400:
                        try:
                            detail = str(resp.json().get("error", {}).get("message", ""))[:140]
                        except Exception:  # noqa: BLE001
                            detail = ""
                        last = f"{model} HTTP {resp.status_code}: {detail or 'no detail'}"
                        break  # wrong/retired model: try the next one
                    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    self.model = model
                    _GOOD_MODEL["m"] = model
                    return parse_json_loose(text)
                except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
                    last = f"{model} {type(exc).__name__}"
                    if isinstance(exc, requests.Timeout):
                        break
        self.warnings.append(f"Gemini failed ({last}); used offline fallback")
        return None


def parse_json_loose(text: str) -> Any:
    """Parse JSON even if wrapped in markdown fences or with stray text around it."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        return json.loads(text)
    except ValueError:
        m = re.search(r"(\{.*\}|\[.*\])", text, flags=re.S)
        if not m:
            raise
        return json.loads(m.group(1))


def llm_from_env() -> LLM:
    return LLM(api_key=config.gemini_api_key(), model=config.gemini_model())
