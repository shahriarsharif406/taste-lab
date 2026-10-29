"""Configuration: everything comes from environment variables (or a local .env file).

Keys are never hard-coded and never sent anywhere except the API they belong to.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_QLOO_BASE_URL = "https://hackathon.api.qloo.com"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_CITIES = ["Austin", "Berlin", "Amsterdam", "Portland", "London"]


def load_dotenv(path: str | os.PathLike = ".env") -> None:
    """Tiny .env loader (KEY=VALUE lines). Does not override existing env vars."""
    p = Path(path)
    if not p.is_file():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def qloo_api_key() -> str | None:
    return os.environ.get("QLOO_API_KEY") or None


def qloo_base_url() -> str:
    return os.environ.get("QLOO_BASE_URL", DEFAULT_QLOO_BASE_URL).rstrip("/")


def clean_key(raw: str | None) -> str | None:
    """Strip whitespace, quotes and any non-ASCII/control characters picked up by copy-paste."""
    if not raw:
        return None
    k = "".join(ch for ch in raw.strip().strip("\"'") if 32 < ord(ch) < 127)
    return k or None


def gemini_api_key() -> str | None:
    return clean_key(os.environ.get("GEMINI_API_KEY"))


def gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)


def force_demo() -> bool:
    return os.environ.get("TASTELAB_DEMO", "").lower() in {"1", "true", "yes"}
