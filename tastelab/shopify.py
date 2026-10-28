"""Read a public product page (e.g. a Shopify product URL) into a product brief.

Safety: only http(s), and hosts that resolve to private/loopback/link-local addresses are
refused, so the app cannot be used to probe internal networks (SSRF).
"""

from __future__ import annotations

import html
import ipaddress
import json
import re
import socket
from urllib.parse import urlparse

import requests


class ProductPageError(ValueError):
    pass


def _check_url(url: str) -> str:
    p = urlparse(url.strip())
    if p.scheme not in {"http", "https"} or not p.hostname:
        raise ProductPageError("Please enter a full http(s) product URL.")
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise ProductPageError("Could not resolve that host.") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ProductPageError("That address is not allowed.")
    return url.strip()


def parse_product_html(page: str) -> dict[str, str]:
    """Extract name/description/price from JSON-LD or OpenGraph tags."""
    out = {"name": "", "description": "", "price": ""}
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, flags=re.S | re.I):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        nodes = data if isinstance(data, list) else [data]
        for node in nodes:
            if isinstance(node, dict) and str(node.get("@type", "")).lower() == "product":
                out["name"] = out["name"] or str(node.get("name", ""))
                out["description"] = out["description"] or str(node.get("description", ""))
                offers = node.get("offers")
                if isinstance(offers, list) and offers:
                    offers = offers[0]
                if isinstance(offers, dict) and offers.get("price"):
                    out["price"] = f'{offers.get("priceCurrency", "")} {offers["price"]}'.strip()

    def meta(prop: str) -> str:
        m = re.search(rf'<meta[^>]+(?:property|name)=["\']{prop}["\'][^>]+content=["\'](.*?)["\']', page, flags=re.I | re.S)
        return html.unescape(m.group(1)).strip() if m else ""

    out["name"] = out["name"] or meta("og:title")
    out["description"] = out["description"] or meta("og:description") or meta("description")
    return {k: html.unescape(v).strip() for k, v in out.items()}


def fetch_product(url: str, session: requests.Session | None = None) -> dict[str, str]:
    safe = _check_url(url)
    s = session or requests.Session()
    try:
        resp = s.get(safe, timeout=12, headers={"User-Agent": "TasteLab/0.1 (+hackathon demo)"},
                     allow_redirects=False)
        if 300 <= resp.status_code < 400 and resp.headers.get("Location"):
            nxt = requests.compat.urljoin(safe, resp.headers["Location"])
            resp = s.get(_check_url(nxt), timeout=12, headers={"User-Agent": "TasteLab/0.1"},
                         allow_redirects=False)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise ProductPageError(f"Could not fetch the page ({type(exc).__name__}).") from exc
    info = parse_product_html(resp.text[:600_000])
    if not info["name"]:
        raise ProductPageError("Could not find a product name on that page.")
    return info
