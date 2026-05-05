"""
Unified CLI Executor — Codex + Claude with smart auto-routing.

Routes:
  auto (default): decides based on task content
  codex: force Codex CLI
  claude: force Claude CLI
  dry-run: print decision, don't actually call CLI

Heuristics for auto-routing:
  - structured / refactor / fix → Codex (explicit control, audit-friendly)
  - creative / explore / design → Claude (autonomous judgment, collaborative)
  - fallback: if one fails, try the other
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Iterator, Optional

from .base import Task, Step

# ── Routing heuristics ──────────────────────────────────────────────
_CODEX_KEYWORDS = [
    "refactor", "修复", "fix", "bug", "structured", "refactoring",
    "restructure", "rewrite", "migrate", "optimize", "lint",
    "type-safe", "type check", "audit", "test", "单元测试",
]
_CLAUDE_KEYWORDS = [
    "design", "设计", "explore", "探索", "creative", "创意",
    "brainstorm", "头脑风暴", "architecture", "架构", "plan",
    "规划", "analyze", "分析", "review", "审查", "explain", "解释",
]


def _decide_cli(content: str) -> str:
    """Returns 'codex' or 'claude' based on content analysis."""
    lower = content.lower()
    codex_score = sum(1 for kw in _CODEX_KEYWORDS if kw in lower)
    claude_score = sum(1 for kw in _CLAUDE_KEYWORDS if kw in lower)

    if codex_score > claude_score:
        return "codex"
    elif claude_score > codex_score:
        return "claude"
    # tie or no match → default to claude for open-ended, codex for code files
    if any(ext in content for ext in [".py", ".ts", ".js", ".go", ".rs"]):
        return "codex"
    return "claude"


# ── CLI invocation ───────────────────────────────────────────────────
def _run_codex(prompt: str, cwd: str, timeout: int = 300) -> tuple[int, str, str]:
    """Run Codex CLI. Returns (exit_code, stdout, stderr)."""
    cmd = ["codex", "exec", "--skip-git-repo-check", "--sandbox", "workspace-write", "--full-auto", prompt]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _run_claude(prompt: str, cwd: str, timeout: int = 300) -> tuple[int, str, str]:
    """Run Claude CLI. Returns (exit_code, stdout, stderr)."""
    cmd = ["claude", "-p", prompt, "--max-turns", "5", "--permission-mode", "bypassPermissions"]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ── Executor class ───────────────────────────────────────────────────
class UnifiedCLIExecutor:
    bot_name = "MAE-CLI-Router"

    def execute(self, task: Task) -> Iterator[Step]:
        cli_choice = task.context.get("cli", "auto")
        cwd = task.context.get("working_dir",
              "/Users/jianan/Projects/local-automation-stack")
        dry_run = task.context.get("dry_run", False)

        # ── Decision ──
        if cli_choice == "auto":
            decision = _decide_cli(task.content)
            reason = (
                f"Codex=structured/refactor, Claude=creative/explore"
            )
        else:
            decision = cli_choice
            reason = "manual override"

        yield Step(
            "🧭 路由决策",
            f"cli={decision} | reason={reason} | dry_run={dry_run}"
        )

        if dry_run:
            yield Step(
                "🔍 Dry-Run",
                f"Would execute via {decision} CLI:\n"
                f"  prompt={task.content[:120]}...\n"
                f"  cwd={cwd}"
            )
            output_path = Path(f"outputs/{task.id}.md")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                f"# Dry-Run Result\n\n"
                f"**Decision:** {decision}\n"
                f"**Reason:** {reason}\n"
                f"**Would run:** `{decision} -p \"{task.content[:80]}...\"`\n"
                f"**CWD:** {cwd}\n",
                encoding="utf-8"
            )
            yield Step("✅ Dry-Run 完成", f"决策已记录 → {output_path}")
            return

        # ── Primary CLI ──
        primary = decision
        fallback_cli = "claude" if primary == "codex" else "codex"

        yield Step(f"🚀 执行 ({primary})", f"prompt 长度={len(task.content)} chars, cwd={cwd}")

        t0 = time.time()
        try:
            if primary == "codex":
                exit_code, stdout, stderr = _run_codex(task.content, cwd)
            else:
                exit_code, stdout, stderr = _run_claude(task.content, cwd)
            elapsed = time.time() - t0
        except subprocess.TimeoutExpired:
            yield Step(f"⏱️ 超时 ({primary})", "超过 5 分钟，尝试 fallback")
            try:
                t0 = time.time()
                if fallback_cli == "codex":
                    exit_code, stdout, stderr = _run_codex(task.content, cwd)
                else:
                    exit_code, stdout, stderr = _run_claude(task.content, cwd)
                elapsed = time.time() - t0
                primary = fallback_cli  # update for reporting
            except subprocess.TimeoutExpired:
                yield Step("❌ 双超时", "Codex 和 Claude 均超时")
                return
            except Exception as e:
                yield Step("❌ Fallback 失败", str(e)[:200])
                return

        # ── Result ──
        yield Step(
            f"📊 {primary} 返回",
            f"exit={exit_code} | stdout={len(stdout)} chars | stderr={len(stderr)} chars | {elapsed:.1f}s"
        )

        output_path = Path(f"outputs/{task.id}.md")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        content = stdout if exit_code == 0 else f"# Error (exit={exit_code})\n\n```\n{stderr[:5000]}\n```"
        output_path.write_text(content, encoding="utf-8")

        if exit_code == 0:
            yield Step("✅ 完成", f"输出 → {output_path}")
        else:
            # Try fallback
            yield Step(f"⚠️ {primary} 失败 (exit={exit_code})", f"尝试 fallback → {fallback_cli}")
            try:
                t0 = time.time()
                if fallback_cli == "codex":
                    exit_code2, stdout2, stderr2 = _run_codex(task.content, cwd)
                else:
                    exit_code2, stdout2, stderr2 = _run_claude(task.content, cwd)
                elapsed2 = time.time() - t0

                if exit_code2 == 0:
                    output_path.write_text(stdout2, encoding="utf-8")
                    yield Step(
                        "✅ Fallback 成功",
                        f"{fallback_cli} | {len(stdout2)} chars | {elapsed2:.1f}s → {output_path}"
                    )
                else:
                    yield Step(
                        "❌ 双失败",
                        f"Both CLIs failed. {primary}: exit={exit_code}, {fallback_cli}: exit={exit_code2}"
                    )
            except Exception as e:
                yield Step("❌ Fallback 异常", str(e)[:200])
