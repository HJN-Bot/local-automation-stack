import subprocess
from .base import Task, Step

# 两个 CLI 都可用，按 task.context 里的 "cli" 字段选择
# 默认 claude，context 里写 "cli": "codex" 则走 codex
CLI_MAP = {
    "claude": ["claude", "-p", "{prompt}", "--max-turns", "5"],
    "codex":  ["codex", "exec", "{prompt}"],
}


class ClaudeCodeExecutor:
    bot_name = "MAE-Coder"

    def execute(self, task: Task):
        cli = task.context.get("cli", "claude")
        cmd_template = CLI_MAP.get(cli, CLI_MAP["claude"])
        working_dir = task.context.get("working_dir",
                      "/Users/jianan/Projects/local-automation-stack")

        yield Step("启动 CLI", f"cli={cli}, cwd={working_dir}")

        cmd = [c.replace("{prompt}", task.content) for c in cmd_template]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=working_dir,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            yield Step("超时", f"{cli} 执行超过 5 分钟")
            return

        yield Step("CLI 返回", f"exit_code={result.returncode}，输出 {len(result.stdout)} 字符")

        output_path = f"outputs/{task.id}.md"
        if result.returncode == 0:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.stdout)
            yield Step("完成", f"已写入 {output_path}")
        else:
            yield Step("失败", f"stderr: {result.stderr[:200]}")
