"""
PipelineExecutor — multi-step plan→execute→checkpoint→aggregate.

Flow:
  1. GLM breaks the task into 3-6 concrete steps (planning phase).
  2. Each step is executed in order; previous step output feeds into the next.
  3. After every step the result is saved to outputs/{task_id}/step_NN.md.
     On restart, completed checkpoints are skipped (idempotent).
  4. Results are aggregated into a single final output file.
  5. Falls back to DeepSeek if GLM fails at any phase.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterator

from .base import Task, Step
from tools.llm import call_deepseek, call_glm
from executors.unified_cli import UnifiedCLIExecutor, _run_codex, _run_claude

_PLAN_PROMPT = """\
You are a precise task planner.
Break the user's request into 3-6 concrete, sequential steps.
Format strictly as:
Step 1: <one-sentence instruction>
Step 2: <one-sentence instruction>
...
No preamble, no explanations — only the numbered steps."""

_STEP_PROMPT = """\
You are a focused executor. Complete the step described below precisely.
Output only the result — no meta-commentary, no step number headers."""

_AGG_PROMPT = """\
Combine the following step-by-step results into one complete, well-structured final answer.
Preserve all key information. Use clear headings where appropriate."""

# ── Research keyword detection ────────────────────────────────────
_RESEARCH_KEYWORDS = (
    "调研", "搜索", "最新", "进展", "对比", "分析现状",
    "market", "research", "latest", "survey", "trend",
)

# ── Code keyword detection for CLI escalation ─────────────────────
_CODE_KEYWORDS = (
    "代码", "修复", "refactor", "fix", "implement", "实现",
    "编写", "重构", "bug", "debug", "test", "测试",
    ".py", ".ts", ".js", ".go", "function", "class",
)

# Maximum sub-pipeline depth to prevent infinite recursion
_MAX_RECURSION_DEPTH = 2


def _needs_search(step_desc: str, task_content: str) -> bool:
    combined = (step_desc + task_content).lower()
    return any(kw in combined for kw in _RESEARCH_KEYWORDS)


def _needs_cli(step_desc: str, task_content: str) -> bool:
    combined = (step_desc + task_content).lower()
    return any(kw in combined for kw in _CODE_KEYWORDS)


def _is_complex_step(result_text: str, step_desc: str) -> bool:
    """Heuristic: should this step be recursively decomposed?"""
    token_estimate = len(result_text) / 3  # rough char→token
    complex_keywords = ("多层", "复杂", "子系统", "pipeline", "multi-step", "workflow")
    has_complex_kw = any(kw in step_desc.lower() for kw in complex_keywords)
    return token_estimate > 2000 or has_complex_kw


def _call_llm(prompt: str, label: str, prefer_search: bool = False) -> tuple[str, dict, str]:
    """Returns (text, usage, model_label).
    Falls back: GLM → DeepSeek. Uses search-enabled GLM when prefer_search=True.
    """
    try:
        if prefer_search:
            from tools.search import call_glm_search
            text, usage = call_glm_search(prompt)
            return text, usage, "GLM-Search"
        text, usage = call_glm(prompt)
        return text, usage, "GLM"
    except Exception as glm_err:
        try:
            text, usage = call_deepseek(prompt)
            return text, usage, f"DeepSeek(GLM-fail:{type(glm_err).__name__})"
        except Exception as ds_err:
            raise RuntimeError(
                f"{label}: GLM failed ({glm_err}); DeepSeek also failed ({ds_err})"
            ) from ds_err


def _call_cli_step(prompt: str, label: str, cwd: str) -> tuple[str, str]:
    """Execute a step via CLI (Codex then Claude fallback).
    Returns (text, model_label).
    """
    try:
        exit_code, stdout, stderr = _run_codex(prompt, cwd, timeout=180)
        if exit_code == 0 and stdout.strip():
            return stdout, "Codex-CLI"
        raise RuntimeError(f"Codex exit={exit_code}: {stderr[:200]}")
    except Exception as codex_err:
        try:
            exit_code, stdout, stderr = _run_claude(prompt, cwd, timeout=180)
            if exit_code == 0 and stdout.strip():
                return stdout, f"Claude-CLI(Codex-fail:{type(codex_err).__name__})"
            raise RuntimeError(f"Claude exit={exit_code}: {stderr[:200]}")
        except Exception as claude_err:
            raise RuntimeError(
                f"{label}: Both CLIs failed. Codex={codex_err}, Claude={claude_err}"
            ) from claude_err


def _parse_steps(text: str) -> list[str]:
    steps = []
    for line in text.splitlines():
        m = re.match(r"^(?:Step\s*)?(\d+)[.:\)]\s+(.+)", line.strip(), re.IGNORECASE)
        if m:
            steps.append(m.group(2).strip())
    return steps


def _load_context(checkpoint_dir: Path, up_to_step: int) -> str:
    parts = []
    for i in range(1, up_to_step + 1):
        cp = checkpoint_dir / f"step_{i:02d}.md"
        if cp.exists():
            parts.append(f"=== Step {i} ===\n{cp.read_text(encoding='utf-8')}")
    return "\n\n".join(parts)


class PipelineExecutor:
    bot_name = "MAE-Pipeline"

    def execute(self, task: Task) -> Iterator[Step]:
        yield Step("规划", "GLM 分解任务为步骤…")

        # Resolve CLI escalation context from task
        cli_cwd = task.context.get("working_dir",
                  "/Users/jianan/Projects/local-automation-stack")
        enable_cli = task.context.get("enable_cli", False)
        recursion_depth = task.context.get("recursion_depth", 0)

        plan_prompt = f"{_PLAN_PROMPT}\n\n任务:\n{task.content}"
        plan_text, _, plan_model = _call_llm(plan_prompt, "planning")

        steps = _parse_steps(plan_text)
        if not steps:
            yield Step("规划", f"无法解析步骤列表，降级为单步执行 [{plan_model}]")
            steps = [task.content]
        else:
            preview = " → ".join(s[:35] for s in steps[:4])
            if len(steps) > 4:
                preview += f" … (+{len(steps) - 4})"
            yield Step("规划完成", f"[{plan_model}] {len(steps)} 步: {preview}")

        checkpoint_dir = Path(f"outputs/{task.id}")
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        (checkpoint_dir / "plan.md").write_text(plan_text, encoding="utf-8")

        for i, step_desc in enumerate(steps, 1):
            cp = checkpoint_dir / f"step_{i:02d}.md"
            if cp.exists():
                yield Step(f"步骤 {i}/{len(steps)} 跳过", f"已有检查点 → {step_desc[:60]}")
                continue

            yield Step(f"步骤 {i}/{len(steps)}", step_desc[:80])

            ctx = _load_context(checkpoint_dir, i - 1)
            step_prompt = (
                f"{_STEP_PROMPT}\n\n"
                f"步骤 {i}/{len(steps)}: {step_desc}\n"
                + (f"\n前序上下文 (最新 2000 字):\n{ctx[-2000:]}\n" if ctx else "")
                + f"\n原始任务:\n{task.content[:600]}"
            )

            # ── Step execution with smart routing ──
            label = f"step-{i}"
            use_search = _needs_search(step_desc, task.content)
            use_cli = enable_cli and _needs_cli(step_desc, task.content)

            routing_note = []
            if use_search:
                routing_note.append("search")
            if use_cli:
                routing_note.append("CLI")
            route_tag = "+".join(routing_note) if routing_note else "API"

            yield Step(f"步骤 {i}/{len(steps)} 路由", f"[{route_tag}] {step_desc[:60]}")

            try:
                if use_cli:
                    result, model_used = _call_cli_step(step_prompt, label, cli_cwd)
                    usage = {}
                else:
                    result, usage, model_used = _call_llm(step_prompt, label, prefer_search=use_search)
            except Exception as e:
                # Final fallback: try DeepSeek API
                try:
                    result, usage = call_deepseek(step_prompt)
                    model_used = f"DeepSeek(final-fallback:{type(e).__name__})"
                except Exception as ds_err:
                    yield Step(f"步骤 {i}/{len(steps)} 失败", str(ds_err)[:200])
                    continue

            cp.write_text(result, encoding="utf-8")

            # Write structured metadata for cost tracking
            meta = {
                "step": i,
                "model": model_used,
                "route": route_tag,
                "tokens_in": usage.get("prompt_tokens", usage.get("input_tokens", 0)),
                "tokens_out": usage.get("completion_tokens", usage.get("output_tokens", 0)),
                "search_used": use_search,
                "cli_used": use_cli,
            }
            (checkpoint_dir / f"step_{i:02d}_meta.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            tokens = meta["tokens_out"] or len(result)
            tok_label = f"{tokens}t" if isinstance(tokens, int) and tokens > 0 else f"{len(result)}c"
            yield Step(f"步骤 {i}/{len(steps)} 完成", f"[{model_used}] {tok_label} → {cp.name}")

            # ── Recursive sub-pipeline for complex steps ──
            if recursion_depth < _MAX_RECURSION_DEPTH and _is_complex_step(result, step_desc):
                yield Step(f"步骤 {i} 递归", f"复杂度高，拆解为子管线 (depth={recursion_depth+1})")
                sub_task = Task(
                    id=f"{task.id}_sub_{i}",
                    type=task.type,
                    content=f"基于以下上下文，进一步拆解并执行:\n{result[:3000]}",
                    context={**task.context, "recursion_depth": recursion_depth + 1},
                )
                sub_executor = PipelineExecutor()
                yield from sub_executor.execute(sub_task)

        # Aggregate
        full_ctx = _load_context(checkpoint_dir, len(steps))
        agg_prompt = (
            f"{_AGG_PROMPT}\n\n原始任务:\n{task.content[:500]}\n\n分步结果:\n{full_ctx[:10000]}"
        )
        # ── Quality gate before aggregation ──
        yield Step("质量门控", "检查步骤输出版本一致性…")
        gate_prompt = (
            "检查以下分步结果，回答 ONLY 'PASS' 或 'WARN: <简短原因>'：\n"
            "1. 有无明显矛盾或互相冲突的结论？\n"
            "2. 有无看起来像编造的数据/论文名/版本号？\n"
            "3. 各步骤输出是否完整（没有截断）？\n\n"
            f"{full_ctx[:5000]}"
        )
        gate_result, _, gate_model = _call_llm(gate_prompt, "quality-gate")
        quality_ok = gate_result.strip().upper().startswith("PASS")
        yield Step(
            "质量门控" if quality_ok else "⚠️ 质量问题",
            f"[{gate_model}] {gate_result.strip()[:150]}"
        )

        final, _, agg_model = _call_llm(agg_prompt, "aggregation")

        if not quality_ok:
            final = (
                f"⚠️ **质量警告** (自动检测)\n> {gate_result.strip()}\n\n"
                f"---\n\n{final}"
            )

        output_path = f"outputs/{task.id}.md"
        Path(output_path).write_text(final, encoding="utf-8")

        # Also write pipeline metadata summary
        meta_summary = {
            "task_id": task.id,
            "task_type": task.type,
            "steps_total": len(steps),
            "models_used": list(set(
                json.loads((checkpoint_dir / f"step_{i:02d}_meta.json").read_text())["model"]
                for i in range(1, len(steps) + 1)
                if (checkpoint_dir / f"step_{i:02d}_meta.json").exists()
            )),
        }
        (checkpoint_dir / "pipeline_meta.json").write_text(
            json.dumps(meta_summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        yield Step("汇总完成", f"[{agg_model}] {len(final)} 字符 → {output_path}")
