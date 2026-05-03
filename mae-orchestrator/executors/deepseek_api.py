import os
from .base import Task, Step
from tools.llm import call_deepseek


class DeepSeekExecutor:
    bot_name = "DeepSeek"

    def execute(self, task: Task):
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-v3")
        yield Step("准备调用", f"模型: {model}，任务类型: {task.type}")

        text, usage = call_deepseek(task.content)

        input_t = usage.get("prompt_tokens", usage.get("input_tokens", 0))
        output_t = usage.get("completion_tokens", usage.get("output_tokens", 0))
        yield Step("API 返回", f"输入 {input_t} / 输出 {output_t} tokens")

        output_path = f"outputs/{task.id}.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)

        yield Step("完成", f"已写入 {output_path}")
