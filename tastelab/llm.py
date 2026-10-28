"""Thin Gemini REST wrapper. If no key is set (or a call fails) callers use deterministic
offline fallbacks, so the pipeline always completes. The key is sent only as a header."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

import requests

from . import config


@dataclass
class LLM:
    api_key: str | None = None
    model: str = config.DEFAULT_GEMINI_MODEL
    timeout: float = 60.0
    session: Any = None
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def __repr__(self) -> str:
        return f"LLM(model={self.model!r}, available={self.available})"

    def json(self, prompt: str, system: str = "") -> Any | None:
        """Ask for a JSON answer. Returns parsed JSON or None (caller falls back)."""
        if not self.available:
            return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json"},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        try:
            resp = self.session.post(url, json=body, timeout=self.timeout,
                                     headers={"x-goog-api-key": self.api_key})
            if resp.status_code >= 400:
                self.warnings.append(f"LLM HTTP {resp.status_code}; used offline fallback")
                return None
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return parse_json_loose(text)
        except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
            self.warnings.append(f"LLM call failed ({type(exc).__name__}); used offline fallback")
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
