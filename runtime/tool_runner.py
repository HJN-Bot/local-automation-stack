"""
Tool runner — executes tool_calls from LLM output and returns results.

The LLM can request tools by including a `tool_calls` list in its JSON response:

  "tool_calls": [
    {"id": "t1", "type": "search",      "args": {"query": "...", "max_results": 5}},
    {"id": "t2", "type": "fetch_url",   "args": {"url": "https://..."}},
    {"id": "t3", "type": "run_python",  "args": {"script": "print('hello')"}},
    {"id": "t4", "type": "run_bash",    "args": {"script": "ls -la"}}
  ]

execute_all() runs each tool and returns a formatted string the harness
appends to task_context as a "tool" message. The LLM then reads the results
on its next invocation and continues reasoning.
"""
from __future__ import annotations

import logging
from typing import Any

from runtime import search as _search
from runtime import code_runner as _code_runner

log = logging.getLogger(__name__)

# Maximum number of tool-use iterations per task cycle (prevents infinite loops)
MAX_TOOL_ITERATIONS = 5

# Supported tool types
_TOOL_TYPES = {"search", "fetch_url", "run_python", "run_bash"}


def execute_all(tool_calls: list[dict[str, Any]]) -> str:
    """
    Execute all tool_calls and return a single formatted string with all results.
    Unknown tool types produce an error entry (never raise).
    """
    if not tool_calls:
        return ""

    parts: list[str] = []
    for call in tool_calls:
        call_id   = call.get("id", "?")
        call_type = call.get("type", "")
        args      = call.get("args", {})

        log.info("tool_runner: executing %s (id=%s)", call_type, call_id)
        result = _dispatch(call_type, args)
        parts.append(f"### Tool result [{call_id}] type={call_type}\n{result}")

    return "\n\n".join(parts)


def _dispatch(call_type: str, args: dict[str, Any]) -> str:
    try:
        if call_type == "search":
            return _search.search(
                query=args["query"],
                max_results=args.get("max_results", 5),
            )
        if call_type == "fetch_url":
            return _search.fetch_url(url=args["url"])
        if call_type == "run_python":
            result = _code_runner.run_python(
                script=args["script"],
                timeout=args.get("timeout"),
            )
            return result.as_text()
        if call_type == "run_bash":
            result = _code_runner.run_bash(
                script=args["script"],
                timeout=args.get("timeout"),
            )
            return result.as_text()
    except KeyError as exc:
        return f"[tool_runner error] Missing required arg: {exc}"
    except Exception as exc:
        log.error("tool_runner: %s failed — %s", call_type, exc)
        return f"[tool_runner error] {exc}"

    return f"[tool_runner error] Unknown tool type: {call_type!r}. Supported: {sorted(_TOOL_TYPES)}"
