import requests
import os
import time
from pathlib import Path
from typing import Optional


def _retry(func, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            wait = 2 ** attempt
            print(f"[retry] attempt {attempt + 1} failed: {e}, wait {wait}s")
            time.sleep(wait)


def _secret(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value:
        return value

    filename = name.lower()
    path = Path.home() / ".openclaw" / "secrets" / filename
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return None


def _call_openai_compatible(base_url: str, api_key: str, model: str, prompt: str) -> tuple[str, dict]:
    if not api_key:
        raise RuntimeError(f"Missing API key for model {model}")

    def _call():
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"], data.get("usage", {})

    return _retry(_call)


def call_deepseek(prompt: str, model: str = None) -> tuple[str, dict]:
    model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-v3")
    return _call_openai_compatible(
        os.getenv("DASHSCOPE_BASE_URL"),
        _secret("DASHSCOPE_API_KEY"),
        model,
        prompt,
    )


def call_glm(prompt: str, model: str = None) -> tuple[str, dict]:
    model = model or os.getenv("GLM_MODEL", "glm-4.6")
    return _call_openai_compatible(
        os.getenv("GLM_BASE_URL", "https://api.z.ai/api/paas/v4"),
        _secret("GLM_API_KEY"),
        model,
        prompt,
    )
