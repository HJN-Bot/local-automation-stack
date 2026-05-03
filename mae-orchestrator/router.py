from dataclasses import dataclass
from executors.deepseek_api import DeepSeekExecutor
from executors.claude_code import ClaudeCodeExecutor
from executors.glm_api import GLMExecutor
from executors.pipeline import PipelineExecutor
from executors.unified_cli import UnifiedCLIExecutor

_cache = {}


def _get(key, factory):
    if key not in _cache:
        _cache[key] = factory()
    return _cache[key]


@dataclass
class RoutingDecision:
    task_type: str
    executor_name: str
    model: str
    bot: str
    reason: str
    fallback: str
    escalation: str = "none"

    def to_step_summary(self) -> str:
        return (
            f"executor={self.executor_name} model={self.model} "
            f"reason={self.reason} fallback={self.fallback} escalation={self.escalation}"
        )


# task_type → (executor_class, model, reason, fallback, escalation)
ROUTING_TABLE = {
    # 便宜任务层：GLM first，DeepSeek 兜底
    "research": (PipelineExecutor, "glm-4-plus", "multi-step research with web_search grounding", "deepseek-v3 per step", "claude/codex for deep analysis steps"),
    "summary":  (GLMExecutor, "glm-4-flash", "cheap routine summary; GLM first",  "deepseek-v3", "codex/claude only if summary fails or needs repo work"),
    "classify": (GLMExecutor, "glm-4-flash", "cheap classification; GLM first",   "deepseek-v3", "none"),
    "write":    (GLMExecutor, "glm-4-flash", "cheap writing task; GLM first",      "deepseek-v3", "codex/claude only for high-stakes rewrite"),
    "review":   (GLMExecutor, "glm-4-flash", "cheap review task; GLM first",       "deepseek-v3", "codex/claude only for codebase review"),
    # 代码任务：GLM 建议 → CLI 执行（auto 路由 Codex/Claude）
    "code":     (UnifiedCLIExecutor, "auto", "GLM advisory + CLI execution with auto-routing", "DeepSeek API fallback", "manual override via --cli codex|claude"),
    "debug":    (UnifiedCLIExecutor, "auto", "GLM advisory + CLI execution with auto-routing", "DeepSeek API fallback", "manual override"),
    "refactor": (UnifiedCLIExecutor, "auto", "GLM advisory + CLI execution with auto-routing", "DeepSeek API fallback", "manual override"),
    # 多步骤任务：规划 → 逐步执行 → 检查点 → 汇总
    "pipeline": (PipelineExecutor, "glm-4-flash", "multi-step plan+execute with per-step checkpoints", "deepseek per step", "claude/codex for hard steps"),
    "project":  (PipelineExecutor, "glm-4-flash", "project-level multi-step task", "deepseek per step", "claude/codex for complex steps"),
    "plan":     (PipelineExecutor, "glm-4-flash", "planning + step execution", "deepseek fallback", "none"),
}

_DEFAULT = (GLMExecutor, "glm-4-flash", "unknown type, GLM first cheap layer", "deepseek-v3", "codex/claude if complex")


def choose_executor(task) -> tuple:
    """返回 (executor实例, RoutingDecision)"""
    cls, model, reason, fallback, escalation = ROUTING_TABLE.get(task.type.lower(), _DEFAULT)
    executor = _get(cls.__name__, cls)

    decision = RoutingDecision(
        task_type=task.type,
        executor_name=cls.__name__,
        model=model,
        bot=executor.bot_name,
        reason=reason,
        fallback=fallback,
        escalation=escalation,
    )
    print(f"[router] {task.type} → {cls.__name__} / {model} / fallback={fallback} / escalation={escalation}")
    return executor, decision
