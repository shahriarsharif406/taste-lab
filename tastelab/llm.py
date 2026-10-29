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

    def pick_model(self) -> str | None:
        """Ask Google which models this key can use; choose the newest plain Flash model."""
        try:
            r = self.session.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                                 headers={"x-goog-api-key": self.api_key}, timeout=20)
            if r.status_code >= 400:
                return None
            names = []
            for m in r.json().get("models", []):
                n = m.get("name", "").removeprefix("models/")
                if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in n \
                        and not any(x in n for x in ("lite", "image", "tts", "live", "audio", "thinking", "robotics", "embed")):
                    names.append(n)
            def key(n: str):
                nums = re.findall(r"\d+(?:\.\d+)?", n)
                return (float(nums[0]) if nums else 0, "preview" not in n and "exp" not in n, n)
            return max(names, key=key) if names else None
        except (requests.RequestException, ValueError):
            return None

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
            if resp.status_code in (400, 404) and not getattr(self, "_retried", False):
                self._retried = True
                alt = self.pick_model()
                if alt and alt != self.model:
                    self.model = alt
                    return self.json(prompt, system)
            if resp.status_code >= 400:
                detail = ""
                try:
                    detail = str(resp.json().get("error", {}).get("message", ""))[:160]
                except Exception:  # noqa: BLE001
                    pass
                self.warnings.append(f"Gemini HTTP {resp.status_code}: {detail or 'no detail'}; used offline fallback")
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
