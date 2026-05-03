import os
from .base import Task, Step
from tools.llm import call_deepseek, call_glm


class GLMExecutor:
    bot_name = "DS-Worker"

    def execute(self, task: Task):
        model = os.getenv("GLM_MODEL", "glm-4.6")
        yield Step("准备调用", f"模型: {model}，任务类型: {task.type}，优先级: GLM-first")

        try:
            text, usage = call_glm(task.content, model=model)
            model_used = model
        except Exception as glm_err:
            yield Step("GLM 失败，切换 DeepSeek", f"{type(glm_err).__name__}: {str(glm_err)[:100]}")
            ds_model = os.getenv("DEEPSEEK_MODEL", "deepseek-v3")
            text, usage = call_deepseek(task.content)
            model_used = ds_model

        input_t = usage.get("prompt_tokens", usage.get("input_tokens", 0))
        output_t = usage.get("completion_tokens", usage.get("output_tokens", 0))
        yield Step("API 返回", f"模型: {model_used}，输入 {input_t} / 输出 {output_t} tokens")

        output_path = f"outputs/{task.id}.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)

        yield Step("完成", f"已写入 {output_path}")
