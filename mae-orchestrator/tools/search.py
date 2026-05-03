"""
GLM web_search tool wrapper — zero new dependencies, uses existing GLM_API_KEY.

GLM-4-plus and glm-4 support native web_search via tool calling.
GLM-4-Flash does NOT support web_search (阉割版).

Usage:
    from tools.search import call_glm_search
    text, usage = call_glm_search("2026年 AI Agent 最新进展")
"""

import os
from tools.llm import _secret, _retry
import requests


def call_glm_search(prompt: str, model: str = None) -> tuple[str, dict]:
    """
    Call GLM with web_search tool enabled.
    Returns (answer_text, usage_dict).

    Falls back to regular GLM call if search-enabled model fails.
    """
    model = model or os.getenv("GLM_SEARCH_MODEL", "glm-4-plus")
    api_key = _secret("GLM_API_KEY")
    base_url = os.getenv("GLM_BASE_URL", "https://api.z.ai/api/paas/v4")

    if not api_key:
        raise RuntimeError("GLM_API_KEY not found")

    def _call():
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a research assistant. Use web_search to find "
                            "current, factual information. Always cite sources when "
                            "using web search results. Output in the user's language."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "tools": [
                    {
                        "type": "web_search",
                        "web_search": {"search_result": True},
                    }
                ],
                "temperature": 0.3,
            },
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        content = choice["message"]["content"]
        usage = data.get("usage", {})

        # If web_search was used, append source info if available
        if "tool_calls" in choice["message"]:
            for tc in choice["message"]["tool_calls"]:
                if tc.get("type") == "web_search":
                    content = f"[Sources from web search]\n\n{content}"

        return content, usage

    try:
        return _retry(_call)
    except Exception as e:
        # Fallback: try glm-4 (may have search, depends on provider)
        if model != "glm-4":
            try:
                return call_glm_search(prompt, model="glm-4")
            except Exception:
                pass
        raise RuntimeError(
            f"GLM search failed with model={model}: {e}. "
            f"Note: glm-4-flash does NOT support web_search."
        ) from e
