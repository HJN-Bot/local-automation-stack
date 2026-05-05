`/Users/jianan/Projects/local-automation-stack/mae-orchestrator/` 顶层目录结构：

**根文件**
- `core.py` — 核心模块
- `router.py` — 任务路由
- `mae_poller.py` — Airtable 轮询入口（10KB，最大）
- `main.py`, `display.py`, `test_day1.py`
- `run_orchestrator.sh` — 启动脚本
- `requirements.txt`, `requirements-edge.txt`
- `.env`

**子目录**
- `demo/` — demo 资料
- `docs/` — 文档
- `edge/` — edge 端代码
- `executors/` — 执行器（Codex、Claude 等）
- `logs/` — 运行日志
- `outputs/` — 任务输出（按 Airtable record id 分目录，如 `recGAigt97U2LbyFn` 等 4 个）
- `skills/` — 空目录（仅 64B）
- `tools/` — 工具
- `venv/`, `__pycache__/` — 环境与缓存

如果需要深入展开某个子目录（比如 `executors/` 或 `docs/`），告诉我即可。
