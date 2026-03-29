"""
Search tools for MAE agents.

Two tools:
  search(query)    — Tavily API: structured results designed for LLM consumption
  fetch_url(url)   — Jina Reader: parse any webpage to clean Markdown (free, no key needed)

Both return text the LLM can directly read and reason over.
"""
from __future__ import annotations

import logging

import requests

from runtime.config import TAVILY_API_KEY

log = logging.getLogger(__name__)

_TAVILY_URL  = "https://api.tavily.com/search"
_JINA_PREFIX = "https://r.jina.ai/"
_TIMEOUT     = 15


def search(query: str, max_results: int = 5) -> str:
    """
    Search the web via Tavily. Returns a plain-text summary the LLM can read.
    Falls back to a descriptive error string (never raises) so the agent can
    decide how to handle the failure.
    """
    if not TAVILY_API_KEY:
        return "[search error] TAVILY_API_KEY not configured."

    payload = {
        "api_key":          TAVILY_API_KEY,
        "query":            query,
        "max_results":      max_results,
        "search_depth":     "basic",
        "include_answer":   True,     # Tavily's own AI summary
        "include_raw_content": False,
    }
    try:
        resp = requests.post(_TAVILY_URL, json=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.error("search: Tavily request failed — %s", exc)
        return f"[search error] {exc}"

    lines: list[str] = [f"## Search: {query}\n"]

    # Tavily's own synthesised answer (often enough on its own)
    if data.get("answer"):
        lines.append(f"**Summary:** {data['answer']}\n")

    for i, r in enumerate(data.get("results", []), 1):
        title   = r.get("title", "—")
        url     = r.get("url", "")
        content = r.get("content", "").strip()
        lines.append(f"{i}. **{title}**\n   {url}\n   {content[:400]}\n")

    return "\n".join(lines)


def fetch_url(url: str) -> str:
    """
    Fetch and parse any URL using Jina Reader (free, no API key required).
    Returns clean Markdown the LLM can read directly.
    Useful for reading API docs, blog posts, GitHub READMEs, etc.
    """
    jina_url = f"{_JINA_PREFIX}{url}"
    try:
        resp = requests.get(
            jina_url,
            headers={"Accept": "text/plain"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        text = resp.text
        # Trim to ~6000 chars to stay within context budget
        if len(text) > 6000:
            text = text[:6000] + "\n\n[... content trimmed ...]"
        log.info("fetch_url: fetched %s (%d chars)", url, len(text))
        return text
    except Exception as exc:
        log.error("fetch_url: failed for %s — %s", url, exc)
        return f"[fetch_url error] {exc}"
